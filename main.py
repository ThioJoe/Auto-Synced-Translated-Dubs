#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Project Title: Auto Synced Translated Dubs (https://github.com/ThioJoe/Auto-Synced-Translated-Dubs)
# Author / Project Owner: "ThioJoe" (https://github.com/ThioJoe)
# License: GPLv3
# NOTE: By contributing to this project, you agree to the terms of the GPLv3 license, and agree to grant the project owner the right to also provide or sell this software, including your contribution, to anyone under any other license, with no compensation to you.

# Import other files
import TTS
import audio_builder
import auth
from utils import parseBool
# Import built in modules
import re
import configparser
import os
import pathlib
# Import other modules
import ffprobe

# EXTERNAL REQUIREMENTS:
# rubberband binaries: https://breakfastquay.com/rubberband/ - Put rubberband.exe and sndfile.dll in the same folder as this script
# ffmpeg installed: https://ffmpeg.org/download.html


# ====================================== SET CONFIGS ================================================
# MOVE THIS INTO A DICTIONARY VARIABLE AT SOME POINT
outputFolder = "output"

# Read config file
config = configparser.ConfigParser()
config.read('config.ini')

skipSynthesize = parseBool(config['SETTINGS']['skip_synthesize'])  # Set to true if you don't want to synthesize the audio. For example, you already did that and are testing

# Translation Settings
skipTranslation = parseBool(config['SETTINGS']['skip_translation'])  # Set to true if you don't want to translate the subtitles. If so, ignore the following two variables
originalLanguage = config['SETTINGS']['original_language']

# Note! Setting this to true will make it so instead of just stretching the audio clips, it will have the API generate new audio clips with adjusted speaking rates
# This can't be done on the first pass because we don't know how long the audio clips will be until we generate them
twoPassVoiceSynth = parseBool(config['SETTINGS']['two_pass_voice_synth'])

#---------------------------------------- Parse Cloud Service Settings ----------------------------------------
# Get auth and project settings for Azure or Google Cloud
cloudConfig = configparser.ConfigParser()
cloudConfig.read('cloud_service_settings.ini')

googleProjectID = cloudConfig['CLOUD']['google_project_id']

#---------------------------------------- Batch File Processing ----------------------------------------

batchConfig = configparser.ConfigParser()
batchConfig.read('batch.ini')
# Get list of languages to process
languageNums = batchConfig['SETTINGS']['enabled_languages'].replace(' ','').split(',')
originalVideoFile = os.path.abspath(batchConfig['SETTINGS']['original_video_file_path'].strip("\""))
srtFile = os.path.abspath(batchConfig['SETTINGS']['srt_file_path'].strip("\""))

# Validate the number of sections
for num in languageNums:
    # Check if section exists
    if not batchConfig.has_section(f'LANGUAGE-{num}'):
        raise ValueError(f'Invalid language number in batch.ini: {num} - Make sure the section [LANGUAGE-{num}] exists')

# Validate the settings in each section
for num in languageNums:
    if not batchConfig.has_option(f'LANGUAGE-{num}', 'synth_language_code'):
        raise ValueError(f'Invalid configuration in batch.ini: {num} - Make sure the option "synth_language_code" exists under [LANGUAGE-{num}]')
    if not batchConfig.has_option(f'LANGUAGE-{num}', 'synth_voice_name'):
        raise ValueError(f'Invalid configuration in batch.ini: {num} - Make sure the option "synth_voice_name" exists under [LANGUAGE-{num}]')
    if not batchConfig.has_option(f'LANGUAGE-{num}', 'translation_target_language'):
        raise ValueError(f'Invalid configuration in batch.ini: {num} - Make sure the option "translation_target_language" exists under [LANGUAGE-{num}]')
    if not batchConfig.has_option(f'LANGUAGE-{num}', 'synth_voice_gender'):
        raise ValueError(f'Invalid configuration in batch.ini: {num} - Make sure the option "synth_voice_gender" exists under [LANGUAGE-{num}]')    

# Create a dictionary of the settings from each section
batchSettings = {}
for num in languageNums:
    batchSettings[num] = {
        'synth_language_code': batchConfig[f'LANGUAGE-{num}']['synth_language_code'],
        'synth_voice_name': batchConfig[f'LANGUAGE-{num}']['synth_voice_name'],
        'translation_target_language': batchConfig[f'LANGUAGE-{num}']['translation_target_language'],
        'synth_voice_gender': batchConfig[f'LANGUAGE-{num}']['synth_voice_gender']
    }

#======================================== Get Total Duration ================================================
# Final audio file Should equal the length of the video in milliseconds
def get_duration(filename):
    import subprocess, json
    result = subprocess.check_output(
            f'ffprobe -v quiet -show_streams -select_streams v:0 -of json "{filename}"', shell=True).decode()
    fields = json.loads(result)['streams'][0]
    try:
        duration = fields['tags']['DURATION']
    except KeyError:
        duration = fields['duration']
    durationMS = round(float(duration)*1000) # Convert to milliseconds
    return durationMS

totalAudioLength = get_duration(originalVideoFile)
#totalAudioLength = 999999 # Or set manually here and comment out the above line

#======================================== Parse SRT File ================================================
# Open an srt file and read the lines into a list
with open(srtFile, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Matches the following example with regex:    00:00:20,130 --> 00:00:23,419
subtitleTimeLineRegex = re.compile(r'\d\d:\d\d:\d\d,\d\d\d --> \d\d:\d\d:\d\d,\d\d\d')

# Create a dictionary
subsDict = {}

# Enumerate lines, and if a line in lines contains only an integer, put that number in the key, and a dictionary in the value
# The dictionary contains the start, ending, and duration of the subtitles as well as the text
# The next line uses the syntax HH:MM:SS,MMM --> HH:MM:SS,MMM . Get the difference between the two times and put that in the dictionary
# For the line after that, put the text in the dictionary
for lineNum, line in enumerate(lines):
    line = line.strip()
    if line.isdigit() and subtitleTimeLineRegex.match(lines[lineNum + 1]):
        lineWithTimestamps = lines[lineNum + 1].strip()
        lineWithSubtitleText = lines[lineNum + 2].strip()
        # Create empty dictionary with keys for start and end times and subtitle text
        subsDict[line] = {'start_ms': '', 'end_ms': '', 'duration_ms': '', 'text': '', 'break_until_next': '', 'srt_timestamps_line': lineWithTimestamps}

        time = lineWithTimestamps.split(' --> ')
        time1 = time[0].split(':')
        time2 = time[1].split(':')

        # Converts the time to milliseconds
        processedTime1 = int(time1[0]) * 3600000 + int(time1[1]) * 60000 + int(time1[2].split(',')[0]) * 1000 + int(time1[2].split(',')[1]) #/ 1000 #Uncomment to turn into seconds
        processedTime2 = int(time2[0]) * 3600000 + int(time2[1]) * 60000 + int(time2[2].split(',')[0]) * 1000 + int(time2[2].split(',')[1]) #/ 1000 #Uncomment to turn into seconds
        timeDifferenceMs = str(processedTime2 - processedTime1)

        # Set the keys in the dictionary to the values
        subsDict[line]['start_ms'] = str(processedTime1)
        subsDict[line]['end_ms'] = str(processedTime2)
        subsDict[line]['duration_ms'] = timeDifferenceMs
        subsDict[line]['text'] = lineWithSubtitleText
        if lineNum > 0:
            # Goes back to previous line's dictionary and writes difference in time to current line
            subsDict[str(int(line)-1)]['break_until_next'] = str(processedTime1 - int(subsDict[str(int(line) - 1)]['end_ms']))
        else:
            subsDict[line]['break_until_next'] = '0'


#======================================== Translate Text ================================================
# Translate the text entries of the dictionary
def translate_dictionary(inputSubsDict, langDict, skipTranslation=False):
    targetLanguage = langDict['targetLanguage']

    for key in inputSubsDict:
        originalText = inputSubsDict[key]['text']
        if skipTranslation == False:
            response = auth.TRANSLATE_API.projects().translateText(
                parent='projects/' + googleProjectID,
                body={
                    'contents':[originalText, 'hello this is a test'],
                    'sourceLanguageCode': originalLanguage,
                    'targetLanguageCode': targetLanguage,
                    'mimeType': 'text/plain',
                    #'model': 'nmt',
                    #'glossaryConfig': {}
                }
            ).execute()
            translatedText = response['translations'][0]['translatedText']
            inputSubsDict[key]['translated_text'] = translatedText
            # Print progress, ovwerwrite the same line
            print(f' Translated: {key} of {len(inputSubsDict)}', end='\r')
        else:
            subsDict[key]['translated_text'] = inputSubsDict[key]['text'] # Skips translating, such as for testing
    print("                                                  ")

    if skipTranslation == False:
        # Use video file name to use in the name of the translate srt file
        translatedSrtFileName = pathlib.Path(originalVideoFile).stem + f" - {targetLanguage}.srt"
        # Set path to save translated srt file
        translatedSrtFileName = os.path.join(outputFolder, translatedSrtFileName)
        # Write new srt file with translated text
        with open(translatedSrtFileName, 'w', encoding='utf-8') as f:
            for key in inputSubsDict:
                f.write(key + '\n')
                f.write(inputSubsDict[key]['srt_timestamps_line'] + '\n')
                f.write(inputSubsDict[key]['translated_text'] + '\n\n')

    return inputSubsDict

#======================================== Translation and Text-To-Speech ================================================    

# Create dictionary to store settings for the language to pass into functions
langDict = {}
for langNum, value in batchSettings.items():
    # Place settings into individual dictionary
    langDict = {
        'targetLanguage': value['translation_target_language'], 
        'voiceName': value['synth_voice_name'], 
        'languageCode': value['synth_language_code'], 
        'voiceGender': value['synth_voice_gender']
        }

    # Create subs dict to use for this language
    individualLanguageSubsDict = dict(subsDict)

    # Print language being processed
    print(f"\n----- Beginning Processing of Language: {langDict['languageCode']} -----")

    # Translate
    individualLanguageSubsDict = translate_dictionary(individualLanguageSubsDict, langDict, skipTranslation=skipTranslation)
    # Synthesize
    individualLanguageSubsDict = TTS.synthesize_dictionary(individualLanguageSubsDict, langDict, skipSynthesize=skipSynthesize)
    # Build audio
    individualLanguageSubsDict = audio_builder.build_audio(individualLanguageSubsDict, langDict, totalAudioLength, twoPassVoiceSynth)
