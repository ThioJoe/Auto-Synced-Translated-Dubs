# Script to automatically update a YouTube video with the translated title, description, and subtitles for each language
import auth
from googleapiclient.errors import HttpError
import copy
import json

videoID = "abcdefghijkl"
translatedJsonFile = r"output\Translated Items.json"

# Override language codes, like for localization. Put the original on the left, and the new on the right
overRiddenLangCodes = {
    "pt": "pt-BR",
}

# ---------------------------------------------------------------------------------------

# Import translated json file
with open(translatedJsonFile, "r", encoding='utf-8') as f:
    translatedJson = json.load(f)

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
    

def update_title_and_description(videoID, translatedJson):
    # Get info about video and original snippet
    originalSnippet, originalLocalizations = get_video_info(videoID)
    newLocals = copy.deepcopy(originalLocalizations)

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
            "description": description
        }

    # Send request to update localization
    localization_result = YOUTUBE_API.videos().update(
        part = "localizations",
        body = {
            "id": videoID,
            "localizations": newLocals
        },
    ).execute()

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

try:
    update_title_and_description(videoID, translatedJson)
except HttpError as hx:
        print(f"An HTTP error {hx.resp.status} occurred:\n{hx.content}")
        errorMessage = str(hx.error_details[0]['message'])
        errorReason = str(hx.error_details[0]['reason'])
        if errorReason == "insufficientPermissions":
            print(f"Error: {errorMessage}.\nThis script requires a different set of permissions for use with YouTube.")
            print("Create a separate project in the Google Cloud Platform, and follow these steps:")
            print("   - Enable the YouTube Data API, grant the scopes: https://www.googleapis.com/auth/youtube.force-ssl")
            print("   - Save the credentials file, but for this one call it 'yt_client_secrets.json'")
