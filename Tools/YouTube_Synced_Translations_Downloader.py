# This script allows the user to tell YouTube to translate the captions of a video into the specified languages
# The resulting srt subtitle files will already be synchronized with the original subtitles

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
import Scripts.translate as translate

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import copy
import json
import langcodes

# Create a dictionary of the settings from each section
languageNums = batchConfig['SETTINGS']['enabled_languages'].replace(' ','').split(',')
batchSettings = {}
for num in languageNums:
    batchSettings[num] = {
        'synth_language_code': batchConfig[f'LANGUAGE-{num}']['synth_language_code'],
        'synth_voice_name': batchConfig[f'LANGUAGE-{num}']['synth_voice_name'],
        'translation_target_language': batchConfig[f'LANGUAGE-{num}']['translation_target_language'],
        'synth_voice_gender': batchConfig[f'LANGUAGE-{num}']['synth_voice_gender']
    }

YOUTUBE_API = auth.youtube_authentication()

def get_captions_list(videoID):
    results = auth.YOUTUBE_API.captions().list(
        part="snippet",
        videoId=videoID
    ).execute()
    return results

def print_caption_list(videoID):
    captions = get_captions_list(videoID)
    print("\nCaption tracks:")
    for index, item in enumerate(captions["items"]):
        name = item["snippet"]["name"] if not item["snippet"]["name"]=="" else "[No Track Name]"
        print(f'{index + 1}. {name} ({item["snippet"]["language"]}): {item["id"]}')

def download_captions(captionID, tlang, tfmt='srt', ):
    results = auth.YOUTUBE_API.captions().download(
        id=captionID,
        tlang=tlang,
        tfmt=tfmt
    ).execute()
    
    # Save captions to file. API call returns bytes in specified format
    with open(f'{videoID}_{tlang}.srt', 'wb') as f:
        # Write the captions bytes to file
        f.write(results)
        
    return results

# Get video ID from user
videoID = input("\nEnter the Video ID: ")

# Check what user wants to do
print("\nWhat do you want to do?")
print(" 1. Download a single translated captions track")
print(" 2. Download all translated captions tracks, based on those chosen in the batch.ini file")
userInput = input("Enter your choice: ")

# Define responses
if userInput == "1":
    userChoice = "single"
elif userInput == "2":
    userChoice = "batch"

if userChoice == "single":
    # Print caption list
    print_caption_list(videoID)

    # Get caption ID from user
    captionID = input("\nEnter the caption ID you want to download: ")

    # Get desired language
    tlang = input("\nEnter the two-letter language code of the captions you want to download: ")

    result = download_captions(captionID, tlang)

    # Save captions to file
    with open(os.path.join(OUTPUT_YTSYNCED_FOLDER, f'{ORIGINAL_VIDEO_NAME} - {tlang}.srt'), 'wb') as f:
        # Write the captions bytes to file
        print("\nSaving captions to file...")
        f.write(result)
        print("Done! File saved to " + os.path.join(OUTPUT_YTSYNCED_FOLDER, f'{ORIGINAL_VIDEO_NAME} - {tlang}.srt'))
        
        
elif userChoice == "batch":
    languageCodeList = []
    # Create list of languages to translate to
    for langNum, langData in batchSettings.items():
        langCode = langData['translation_target_language']
        languageCodeList.append(langCode)
        
    # List languages to download
    print("\nDownloading captions for the following languages:")
    print(languageCodeList)
    input("\nPress Enter to continue...")
    
    # Download auto translated captions
    translate.download_youtube_auto_translations(languageCodeList, videoID)
