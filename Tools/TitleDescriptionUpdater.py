# Script to automatically update a YouTube video with the translated title, description, and subtitles for each language
# ================================================================================================================
videoID = "abcdefghijkl"
translatedJsonFile = r"Outputs\Translated Items.json"
subtitlesFolder = r"output"

updateTitleAndDescription = True
uploadSubtitles = True

# Override language codes, like for localization. Put the original on the left, and the new on the right
overRiddenLangCodes = {
    "pt": "pt-BR",
}

# ================================================================================================================

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
from Scripts.shared_imports import *
import Scripts.auth as auth

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import copy
import json

import langcodes

# Import translated json file
with open(translatedJsonFile, "r", encoding='utf-8') as f:
    translatedJson = json.load(f)

YOUTUBE_API = auth.youtube_authentication()

# ---------------------------------------------------------------------------------------

################################ Subtitles ################################
if uploadSubtitles:
    # Process subtitles to upload
    subtitleFilesDict = {}

    # Get list of subtitle files in the directory
    for file in os.listdir(subtitlesFolder):
        if file.endswith(".srt"):
            nameNoExt = os.path.splitext(file)[0]
            # Get the language code from the end of the filename. Assumes the code will be separated by ' - '
            if ' - ' in nameNoExt:
                parsedLanguageCode = nameNoExt.split(' - ')[-1].strip()
            else:
                # Print error and ask whether to continue
                print(f"\nWARNING: Could not find language code in filename: {file}")
                print("\nTo read the language code, separate the language code from the rest of the filename with: ")
                print("     ' - ' (a dash surrounded by spaces)")
                print("For example:   'Whatever Video - en-us.wav'")
                print("Enter 'y' to skip that track and conitnue, or enter anything else to exit.")

                userInput = input("Continue Anyway? (y/n): ")
                if userInput.lower() != 'y':
                    sys.exit()

            # Check if the language code is valid, if so save to dictionary for next steps
            try:
                langObject = langcodes.get(parsedLanguageCode)
                threeLetterCode = langObject.to_alpha3()
                languageDisplayName = langcodes.get(threeLetterCode).display_name()
                # Add to dictionary
                subtitleFilesDict[parsedLanguageCode] = file

            except:
                print(f"\nWARNING: Language code '{parsedLanguageCode}' is not valid for file: {file}")
                print("Enter 'y' to skip that track and conitnue, or enter anything else to exit.")
                userInput = input("\nContinue Anyway and Skip File? (y/n): ")
                if userInput.lower() != 'y':
                    sys.exit()         


def list_captions(videoID):
    results = auth.YOUTUBE_API.captions().list(
        part="snippet",
        videoId=videoID
    ).execute()
    return results
#captionsList = list_captions(videoID)

def delete_caption_track(videoID, captionID):
    delete_result = auth.YOUTUBE_API.captions().delete(
        id=captionID
    ).execute()
    return delete_result
#captionsTrackID = "abcdefghijkl"
#delete_result = delete_caption_track(videoID, captionsTrackID)


def upload_caption(videoID, language, name, file):
    # Convert file to bytes
    subtitleData = MediaFileUpload(file, mimetype="text/plain", resumable=True)

    insert_result = auth.YOUTUBE_API.captions().insert(
        part="snippet",
        body=dict(
            snippet=dict(
                videoId=videoID,
                language=language,
                name=name,
                isDraft=False
            )
        ),
        media_body=subtitleData
    ).execute()
    pass

# ---------------------------------------------------------------------------------------

################################ Title and Description ################################

def get_video_info(videoID):
    response = YOUTUBE_API.videos().list(
        part = "snippet,localizations",
        id = videoID
    ).execute()
    #return response
    snippet = response["items"][0]["snippet"]
    localizations = response["items"][0]["localizations"]
    return snippet, localizations
    

def update_title_and_description(videoID, translatedJson):
    # Get info about video and original snippet
    originalSnippet, originalLocalizations = get_video_info(videoID)
    newLocals = copy.deepcopy(originalLocalizations)
    categoryId = originalSnippet['categoryId']

    # newSnippet = copy.deepcopy(originalSnippet) 
    # def update_snippet():
    #     # Update video snippet: Title, Description, etc
    #     snippet_result = YOUTUBE_API.videos().update(
    #         part = "snippet",
    #         body = {"id": videoID, "snippet": newSnippet}
    #     ).execute()

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

    try:
        # Send request to update localization
        localization_result = YOUTUBE_API.videos().update(
            part = "localizations,snippet",
            body = {
                "id": videoID,
                "localizations": newLocals,
                #"categoryId": categoryId
                #"snippet": originalSnippet
            },
        ).execute()

    except HttpError as hx:
        print(f"An HTTP error {hx.resp.status} occurred:\n{hx.content}")
        errorMessage = str(hx.error_details[0]['message'])
        errorReason = str(hx.error_details[0]['reason'])
        if errorReason == "insufficientPermissions":
            print(f"Error: {errorMessage}.\nThis script requires a different set of permissions for use with YouTube.")
            print("Create a separate project in the Google Cloud Platform, and follow these steps:")
            print("   - Enable the YouTube Data API, grant the scopes: https://www.googleapis.com/auth/youtube.force-ssl")
            print("   - Save the credentials file, but for this one call it 'yt_client_secrets.json'")

# ---------------------------------------------------------------------------------------    

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
   

# ---------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------

# Get video title to confirm
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

# ---------------------------------------------------------------------------------------

if updateTitleAndDescription:
    # Update titles and descriptions
    print("\nUpdating titles and descriptions...")
    update_title_and_description(videoID, translatedJson)

if uploadSubtitles:
    # Upload captions
    for langCode, fileName in subtitleFilesDict.items():
        # Get language display name
        languageDisplayName = langcodes.get(langCode).display_name()
        # Get file path
        filePath = os.path.join(subtitlesFolder, fileName)
        # Upload the caption
        print("\nUploading caption for language: " + languageDisplayName + " (" + langCode + ")")
        upload_caption(videoID, langCode, "", filePath) # Use empty string as the name, so it will apply as the default caption for that language

print("\nDone!")
