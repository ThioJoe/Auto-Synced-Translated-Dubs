# This script prompts the user to input a video ID, and then it lists the caption tracks and their IDs. The user can then input one or more caption IDs separated by commas to delete the selected captions.

# Set working diretory to one level up, so that the scripts folder is in the path
import os
import sys
# Check if current folder is named "Tools"
if os.path.basename(os.getcwd()) == 'Tools':
    os.chdir('..')
# Check if current folder contains a folder named "Tools"
elif 'Tools' in os.listdir():
    pass
else:
    print("Warning: Not currently in the 'Tools' folder. The script may not work properly.")
    

# Set the path to include the project root folder, so Scripts imports are valid
sys.path.insert(1, os.getcwd())
# ---------------------------------------------------------------------------------------

overRiddenLangCodes = {
    "pt": "pt-BR",
    #"es": "es-US",
}

import Scripts.auth as auth
import copy

YOUTUBE_API = auth.youtube_authentication()

def get_video_info(videoID):
    response = YOUTUBE_API.videos().list(
        part = "snippet,localizations",
        id = videoID
    ).execute()
    #return response
    snippet = response["items"][0]["snippet"]
    localizations = response["items"][0]["localizations"]
    return snippet, localizations

def get_video_localizations(videoID):
    response = YOUTUBE_API.videos().list(
        part = "localizations",
        id = videoID
    ).execute()
    localizations = response["items"][0]["localizations"]
    return localizations

def list_captions(videoID):
    results = auth.YOUTUBE_API.captions().list(
        part="snippet",
        videoId=videoID
    ).execute()
    return results
	
def delete_caption_track(videoID, captionID):
    delete_result = auth.YOUTUBE_API.captions().delete(
        id=captionID
    ).execute()
    return delete_result

def update_title_and_description(videoID, translatedJson):
    # Get info about video and original snippet
    originalSnippet, originalLocalizations = get_video_info(videoID)
    newLocals = copy.deepcopy(originalLocalizations)
    categoryId = originalSnippet['categoryId']
    
        # Apply all the languages to the newLocals dictionary
    for langNum, langData in translatedJson.items():
        # Get entries
        langCode = langData["translation_target_language"]
        title = langData["translated_title"]
        description = langData["translated_description"]

        # Override selected language codes if applicable
        if overRiddenLangCodes and langCode in overRiddenLangCodes:
            langCode = overRiddenLangCodes[langCode]

        # newLocals will contain the original localizations, but overwritten by the data from the json file
        newLocals[langCode] = {
            "title": title,
            "description": description,
            #"categoryId": categoryId
        }

def get_video_title(videoID):
    try:
        results = auth.YOUTUBE_API.videos().list(
            part="snippet",
            id=videoID,
            fields="items/snippet/title",
            maxResults=1
        ).execute()
    except HttpError as hx:
        print(hx)

    if results['items']:
        title = results["items"][0]["snippet"]["title"]
        return title
    else:
        print("Something went wrong. No video found.")
        return None

def add_captions_to_dict(videoID, videoLanguagesDict, videoDefaultLanguage):
    results = auth.YOUTUBE_API.captions().list(
        part="snippet",
        videoId=videoID
    ).execute()
    
    for index, item in enumerate(results["items"]):
        name = item["snippet"]["name"] if not item["snippet"]["name"]=="" else "[No Track Name]"
        id = item["id"]
        langCode = item["snippet"]["language"]
        #print(f'{index + 1}. {name} ({item["snippet"]["language"]}): {item["id"]}')
        
        # Skip if the language code is the same as the default language
        if not langCode == videoDefaultLanguage:
            index = 1
            # Check if the dictionary already contains a key for this language code
            if langCode in videoLanguagesDict:
                # Each language key will have subkeys with indexes for multiple tracks, so add to the first available index
                # Start counting up from 1 and check if the key exists
                while True:
                    if index in videoLanguagesDict[langCode]['subtitles']:
                        index += 1
                    else:
                        break
                    
                # Add to dictionary
                videoLanguagesDict[langCode]['subtitles'][index] = {
                    "subtitleName": name,
                    "subtitleID": id
                }
            
            else:
                # Create a new entry for this language code
                videoLanguagesDict[langCode] = {
                    "subtitles": {
                        1: {
                            "subtitleName": name,
                            "subtitleID": id
                        },
                    },
                    "localizations": {}
                }
    return videoLanguagesDict

def add_localizations_to_dict(videoID, videoLanguagesDict, videoDefaultLanguage):
    # First get localizations. It returns a dictionary
    localizations = get_video_localizations(videoID)
    
    for langCode, localData in localizations.items():
        # Don't add if the same as default language
        if not langCode == videoDefaultLanguage:
            # Check if the dictionary already contains a key for this language code
            if langCode in videoLanguagesDict:
                # Add to dictionary
                videoLanguagesDict[langCode]['localizations'] = {
                    'title': localData['title'],
                    'description': localData['description']
                }
            else:
                # Create a new entry for this language code
                videoLanguagesDict[langCode] = {
                    "subtitles": {},
                    "localizations": {
                        'title': localData['title'],
                        'description': localData['description']
                    }
                }
    return videoLanguagesDict

def display_languages(video_languages_dict):
    print("\nAvailable Languages (Original Language is Not Included):")
    lang_index = 1
    for lang_code, data in video_languages_dict.items():
        has_localization = bool(data.get('localizations'))
        subtitle_count = len(data.get('subtitles', {}))

        # Base line with language code
        base_line = f"{lang_index}. {lang_code}:"
        base_length = len(base_line)

        # Adding Translated Title & Description info
        title_desc_info = f"[{'x' if has_localization else ' '}] Translated Title & Description"
        line = base_line.ljust(base_length + 3) + title_desc_info
        print("")
        print(line)

        # Subtitle info on a new line, aligned
        subtitle_info = f"[{'x' if subtitle_count > 0 else ' '}] Subtitle Tracks ({subtitle_count})"
        print(' ' * (base_length + 3) + subtitle_info)

        # Displaying individual subtitle tracks if more than one
        if subtitle_count > 1:
            for sub_index, subtitle_info in enumerate(data['subtitles'].values(), 1):
                print(f"{' ' * (base_length + 6)}{lang_index}.{sub_index} {subtitle_info['subtitleName']} (ID: {subtitle_info['subtitleID']})")

        lang_index += 1
        
def parse_subtitle_indices(input_string, video_languages_dict):
    if input_string.strip().lower() == 'none' or input_string.strip() == '':
        return {}
    elif input_string == 'all':
        return {lang_code: list(data['subtitles'].keys()) for lang_code, data in video_languages_dict.items() if 'subtitles' in data and data['subtitles']}
    
    raw_indices = [index.strip() for index in input_string.split(',')]
    subtitles_to_delete = {}

    for index in raw_indices:
        parts = index.split('.')
        if len(parts) == 1:
            lang_code = list(video_languages_dict.keys())[int(parts[0]) - 1]
            # Add all subtitles of this language to deletion list
            subtitles_to_delete[lang_code] = list(video_languages_dict[lang_code]['subtitles'].keys())
        elif len(parts) == 2:
            lang_code = list(video_languages_dict.keys())[int(parts[0]) - 1]
            subtitle_index = int(parts[1])
            subtitles_to_delete.setdefault(lang_code, []).append(subtitle_index)
    
    return subtitles_to_delete

def parse_localization_indices(input_string, video_languages_dict, subtitle_indices):
    if input_string.strip().lower() == 'same':
        return list(subtitle_indices.keys())
    elif input_string.strip().lower() == 'none' or input_string.strip() == '':
        return []
    elif input_string.strip().lower() == 'all':
        return list(video_languages_dict.keys())

    raw_indices = [index.strip() for index in input_string.split(',')]
    localizations_to_delete = []

    for index in raw_indices:
        lang_code = list(video_languages_dict.keys())[int(index) - 1]
        localizations_to_delete.append(lang_code)

    return localizations_to_delete

def remove_translated_title_and_description(videoID, langCodesList):
    # Get original localizations
    originalLocals = get_video_localizations(videoID)
    allNewLocals = copy.deepcopy(originalLocals)
    
    for langCode in langCodesList:
        # Remove the entire language key per language code
        allNewLocals.pop(langCode, None)
    
    localization_result = YOUTUBE_API.videos().update(
        part = "localizations,snippet",
        body = {
            "id": videoID,
            "localizations": allNewLocals,
            #"categoryId": categoryId
            #"snippet": originalSnippet
        },
    ).execute()


# ---------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------

def main(videoID=None):
    if videoID == None:
        print("\nEnter a video ID to get a list of the subtitle tracks on the video. You will then have the option to delete any of the tracks.")
        videoID = input("\nEnter the Video ID: ")
        
    videoTitle = get_video_title(videoID)
    print("----------------------------------------")
    print("\nConfirm this is the video you want to apply the translated titles and descriptions to.")
    print(f"\n >>> Video To Be Updated: {videoTitle} <<<")
    choice = input("\nIs the above video correct? (y/n) ")
    if choice.lower() == "n":
        print("Exiting...")
        exit()
    elif choice.lower() == "y":
        pass
        
    deleteSubtitles = False
    deleteLocalizations = False

    # Get video information
    snippet, localizations = get_video_info(videoID)
    videoDefaultLanguage = snippet['defaultLanguage']
    videoDefaultAudioLanguage = snippet['defaultAudioLanguage']
    
    # Create dictionary for each language, will put info about captions, localizations for each into it
    videoLanguagesDict = {}
    # Put subtitles into dictionary
    videoLanguagesDict = add_captions_to_dict(videoID, videoLanguagesDict, videoDefaultLanguage)
    # Put localizations (aka title and description translations) into dictionary
    videoLanguagesDict = add_localizations_to_dict(videoID, videoLanguagesDict, videoDefaultLanguage)
    
    
    # Display languages
    display_languages(videoLanguagesDict)

    # Get subtitle deletion indices
    print("\nEnter the index numbers of the language to delete (e.g., 1, 2.1, 3.2, separated by commas).")
    print("  > Type 'none' to skip, or 'all' to select all.")
    print("  > You can select individual subtitle tracks (if there are multiple for a language) by doing  1.1, 2.2, etc.")
    selected_subtitle_indices = input("\nEnter Here: ")
    subtitles_to_delete = parse_subtitle_indices(selected_subtitle_indices, videoLanguagesDict)

    # Get localization deletion indices
    print("\nEnter the index numbers of the localizations to delete (type 'same' to select the same as subtitles, separated by commas).")
    print("  > Type 'none' to skip, or 'all' to select all, or 'same' to select the same as subtitles (if any).")
    selected_localization_indices = input("\nEnter Here: ")
    localizations_to_delete = parse_localization_indices(selected_localization_indices, videoLanguagesDict, subtitles_to_delete)
    
    # Ask for confirmation
    print("\nSubtitles to Delete:", subtitles_to_delete)
    print("Translated Titles & Descriptions to Delete:", localizations_to_delete)
    choice = input("\nIs this correct? (y/n) ")
    if choice.lower() == "n":
        print("Exiting...")
        exit()
    elif choice.lower() == "y":
        pass
        
    # Delete the selected subtitles
    if subtitles_to_delete:
        for langCode, indices in subtitles_to_delete.items():
            for caption_index in indices:
                captionID = videoLanguagesDict[langCode]['subtitles'][caption_index]['subtitleID']
                delete_result = delete_caption_track(videoID, captionID)
                print(f"Deleted {langCode} caption with ID: {captionID}")
                
    # Delete selected localizations
    if localizations_to_delete:
        remove_translated_title_and_description(videoID, localizations_to_delete)
        print(f"Deleted translated titles & descriptions for: {localizations_to_delete}")

    # for index in indices:
    #     captionID = captions["items"][index]["id"]
    #     delete_result = delete_caption_track(videoID, captionID)
    #     print(f"Deleted caption {captionID}")

if __name__ == "__main__":
    main()