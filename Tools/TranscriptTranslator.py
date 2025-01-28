# Translates entire transcripts
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
from Tools.SubtitlesTitleDescriptionRemover import main as remove_tracks
import Scripts.auth as auth
import Scripts.translate as translate

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import copy
import json
import langcodes

# Check to ensure the translated language isn't the same as the original. If it is, warn the user and ask if they want to continue
originalLanguage = config.original_language
originalLanguage2Letter = langcodes.get(config.original_language).language
for num in batchConfig['SETTINGS']['enabled_languages'].replace(' ','').split(','):
    # Need to convert original language BPC-47 code to 2-letter code
    targetLanguage = batchConfig[f'LANGUAGE-{num}'][LangDataKeys.translation_target_language]
    if targetLanguage == originalLanguage2Letter:
        print(f"\n WARNING: One of the translation languages set in batch.ini ({targetLanguage}) is the same as the original language set in config.ini ({originalLanguage}) !")
        print("  > Note: Transcript will be translated into languages set in batch.ini\n")
        input("Continue Anyway? (Press Enter to continue...)")
        break

# Get file path from user for native original transcript
print("----------------------------------------")
print("\n  > Note: Transcript will be translated into languages set in batch.ini\n")
nativeTranscriptFilePath = input("Enter the file path for the native original transcript: ")

# Define paths
baseFilename = os.path.basename(nativeTranscriptFilePath)
filenameStem = os.path.splitext(baseFilename)[0]
transcriptOutputDirectory = os.path.join(OUTPUT_DIRECTORY, 'Translated Transcripts')

# Read transcript file
with open(nativeTranscriptFilePath, 'r', encoding='utf-8') as f:
    transcript = f.read()

# Create output directory if it doesn't exist
if not os.path.exists(transcriptOutputDirectory):
    os.makedirs(transcriptOutputDirectory)

# Create a dictionary of the settings from each section
languageNums = batchConfig['SETTINGS']['enabled_languages'].replace(' ','').split(',')
batchSettings = {}
for num in languageNums:
    batchSettings[num] = {
        'synth_language_code': batchConfig[f'LANGUAGE-{num}']['synth_language_code'],
        'synth_voice_name': batchConfig[f'LANGUAGE-{num}']['synth_voice_name'],
        'translation_target_language': batchConfig[f'LANGUAGE-{num}'][LangDataKeys.translation_target_language],
        'synth_voice_gender': batchConfig[f'LANGUAGE-{num}']['synth_voice_gender']
    }
# Set which translation services for each language, formality, etc
batchSettings = translate.set_translation_info(batchSettings)

# ---------------------------------------------------------------------------------------

def process_language(langData, processedCount, totalLanguages):
    langDict = {
        'targetLanguage': langData[LangDataKeys.translation_target_language], 
        'voiceName': langData['synth_voice_name'], 
        'languageCode': langData['synth_language_code'], 
        'voiceGender': langData['synth_voice_gender'],
        'translateService': langData['translate_service'],
        'formality': langData[LangDataKeys.formality]
        }

    print(f"\n----- Beginning Processing of Language ({processedCount}/{totalLanguages}): {langDict[LangDictKeys.languageCode]} -----")

    # Set final file path
    translatedTranscriptFilePath = os.path.join(transcriptOutputDirectory, f"{filenameStem} - {langDict[LangDictKeys.targetLanguage]}.txt")

    # Split transcript into chunks of 5000 characters to avoid exceeding the character limits
    transcriptChunkedList = translate.split_transcript_chunks(transcript, 5000)

    # Need to convert the list of chunks into a compatible dictionary to be used with 'translate_dictionary' function
    convertedDict = translate.convertChunkListToCompatibleDict(transcriptChunkedList)

    # Translate the dictionary text, while processing with custom rules
    translatedDict = translate.translate_dictionary(convertedDict, langDict, transcriptMode=True)

    # Convert dictionary back to transcript string
    translatedChunkList = []
    for key, value in translatedDict.items():
        translatedChunkList.append(value[SubsDictKeys.translated_text])
        
    translatedTranscript = " ".join(translatedChunkList)

    # Save translated transcript to file
    with open(translatedTranscriptFilePath, 'w', encoding='utf-8') as f:
        f.write(translatedTranscript)

    print("Finished translating transcript.")
    print("File Location: " + translatedTranscriptFilePath)
    

# ---------------------------------------------------------------------------------------
processedCount=0
totalLanguages = len(batchSettings)
for langNum, langData in batchSettings.items():
    processedCount += 1
    # Process current fallback language
    process_language(langData, processedCount, totalLanguages)
