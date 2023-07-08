# Script to upload a translated transcript to YouTube, and use the auto-sync feature to sync it to the video.
# ================================================================================================================

# ---------------------------------------------------------------------------------------
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
from Tools.SubtitleTrackRemover import main as remove_tracks
import Scripts.auth as auth

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import copy
import json
import langcodes

YOUTUBE_API = auth.youtube_authentication()


def list_captions(videoID):
    results = auth.YOUTUBE_API.captions().list(
        part="snippet",
        videoId=videoID
    ).execute()
    return results
#captionsList = list_captions(videoID)

def print_caption_info(videoID):
    captionsResponseDict = list_captions(videoID)
    
    items = captionsResponseDict['items']
    print("\n----------- Caption Tracks -----------\n")
    for item in items:
        snippet = item['snippet']
        language = langcodes.get(snippet['language']).display_name()
        status = snippet['status']
        isAutoSynced = snippet['isAutoSynced']
        isDraft = snippet['isDraft']
        
        print(f'Language: {language}')
        print(f'Status: {status}')
        print(f'Is Auto Synced: {isAutoSynced}')
        print(f'Is Draft: {isDraft}')
        print()


def upload_caption(videoID, language, name, file, sync=False, isDraft=False):
    # Convert file to bytes
    subtitleData = MediaFileUpload(file, mimetype="text/plain", resumable=True)

    insert_result = auth.YOUTUBE_API.captions().insert(
        part="snippet",
        sync=sync,
        body=dict(
            snippet=dict(
                videoId=videoID,
                language=language,
                name=name,
                isDraft=isDraft
            )
        ),
        media_body=subtitleData
    ).execute()
    pass


def get_video_info(videoID):
    response = YOUTUBE_API.videos().list(
        part = "snippet,localizations",
        id = videoID
    ).execute()
    #return response
    snippet = response["items"][0]["snippet"]
    localizations = response["items"][0]["localizations"]
    return snippet, localizations

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

# Get video ID from user
print("\nEnter the video ID of the video you want to apply the translations to.")
videoID = input("Video ID: ")

# Get video title to confirm
videoTitle = get_video_title(videoID)
print("----------------------------------------")
print("\nConfirm this is the video you want to apply the translations to.")
print(f"\n >>> Video To Be Updated: {videoTitle} <<<")
choice = input("\nIs the above video correct? (y/n) ")
if choice.lower() == "n":
    print("Exiting...")
    exit()
elif choice.lower() == "y":
    pass

# Ask what to do
print("\nWhat would you like to do?")
print("  1. Upload a single transcripti file to YouTube, and sync it to the video.")
print("  2. Upload multiple transcript files to YouTube, and sync them to the video.")
print("  ---------------------------------------------------------------------------")
print("  3. Check the existing captions (including sync status) for this video.")
print("  4. Remove a caption track from this video.")
userInput = input("\nEnter 1 or 2: ")
if userInput == "1":
    userChoice = "uploadSingleTranscript"
if userInput == "2":
    userChoice = "uploadMultipleTranscripts"
elif userInput == "3":
    userChoice = "checkCaptionStatus"
elif userInput == "4":
    userChoice = "removeCaptionTrack"

if userChoice == "uploadSingleTranscript":
    # Get two-letter language code from user
    print("\nManual Transcript Sync Mode: Upload a transcript file to YouTube, and it will be synced to the video.")
    langCode = input("\nEnter two-letter language code: ")
    languageDisplayName = langcodes.get(langCode).display_name()

    # Confirm language
    print("\nConfirm language code: " + languageDisplayName + " (" + langCode + ")")
    choice = input("\nIs the above language code correct? (y/n) ")
    if choice.lower() == "n":
        print("Exiting...")
        exit()

    # Get file path of transcript file from user
    filePath = input("\nEnter file path of transcript file (Drag file into window): ")
    print("\nUploading caption for language: " + languageDisplayName + " (" + langCode + ")")

    upload_caption(videoID, langCode, "", filePath,sync=True, isDraft=False) # Use empty string as the name, so it will apply as the default caption for that language)
    print("\nDone. Retrieving latest caption track statuses. Note: It may take a while for the caption to be synced to the video.")
    print_caption_info(videoID)
    
elif userChoice == "checkCaptionStatus":
    print_caption_info(videoID)
    
elif userChoice == "removeCaptionTrack":
    remove_tracks(videoID)
    
elif userChoice == "uploadMultipleTranscripts":
    # Get the folder path from the user
    print("\nMultiple Transcript Sync Mode: Enter the folder path containing the translated transcription text files.")
    print("Tip: You can just drag one of them into the Window to automatically detect the path.")
    userPathInput = input("\nFolder Path: ")
    
    # Get the path
    if os.path.isdir(userPathInput):
        folderPath = userPathInput
    elif os.path.isfile(userPathInput):
        folderPath = os.path.dirname(userPathInput)
        
    # Process files to upload
    transcriptFilesDict = {}
    
    # Get the list of files in the folder, add to dictionary
    for file in os.listdir(folderPath):
        if file.endswith(".txt"):
            nameNoExt = os.path.splitext(file)[0]
            # Get the language code from the end of the filename. Assumes the code will be separated by ' - '
            if ' - ' in nameNoExt:
                parsedLanguageCode = nameNoExt.split(' - ')[-1].strip()
            else:
                # Print error and ask whether to continue
                print(f"\nWARNING: Could not find language code in filename: {file}")
                print("\nTo read the language code, separate the language code from the rest of the filename with: ")
                print("     ' - ' (a dash surrounded by spaces)")
                print("For example:   'Whatever Video - en.txt'")
                print("Enter 'y' to skip that file and conitnue, or enter anything else to exit.")

                userInput = input("Continue Anyway? (y/n): ")
                if userInput.lower() != 'y':
                    sys.exit()
                    
            # Check if the language code is valid, if so save to dictionary for next steps
            try:
                langObject = langcodes.get(parsedLanguageCode)
                threeLetterCode = langObject.to_alpha3()
                languageDisplayName = langcodes.get(threeLetterCode).display_name()
                # Add to dictionary
                transcriptFilesDict[parsedLanguageCode] = file

            except:
                print(f"\nWARNING: Language code '{parsedLanguageCode}' is not valid for file: {file}")
                print("Enter 'y' to skip that track and conitnue, or enter anything else to exit.")
                userInput = input("\nContinue Anyway and Skip File? (y/n): ")
                if userInput.lower() != 'y':
                    sys.exit()

    # Begin uploading
    for langCode, fileName in transcriptFilesDict.items():
        filePath = os.path.join(folderPath, fileName)
        print("\nUploading caption for language: " + languageDisplayName + " (" + langCode + ")")
        upload_caption(videoID, langCode, "", filePath, sync=True, isDraft=False) # Use empty string as the name, so it will apply as the default caption for that language)
