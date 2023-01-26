#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Project Title: Auto Synced Translated Dubs (https://github.com/ThioJoe/Auto-Synced-Translated-Dubs)
# Author / Project Owner: "ThioJoe" (https://github.com/ThioJoe)
# License: GPLv3
# NOTE: By contributing to this project, you agree to the terms of the GPLv3 license, and agree to grant the project owner the right to also provide or sell this software, including your contribution, to anyone under any other license, with no compensation to you.

version = '0.10.0'
print(f"------- 'Auto Synced Translated Dubs' script by ThioJoe - Release version {version} -------")

# Import other files
import TTS
import audio_builder
import auth
import translate
from utils import parseBool

# Import built in modules
import re
import configparser
import os
import copy

# Import other modules
import ffprobe
import sys

# EXTERNAL REQUIREMENTS:
# rubberband binaries: https://breakfastquay.com/rubberband/ - Put rubberband.exe and sndfile.dll in the same folder as this script
# ffmpeg installed: https://ffmpeg.org/download.html


# ====================================== SET CONFIGS ================================================
# MOVE THIS INTO A DICTIONARY VARIABLE AT SOME POINT


# Read config file
config = configparser.ConfigParser()
config.read('config.ini')

skipSynthesize = parseBool(config['SETTINGS']['skip_synthesize'])  # Set to true if you don't want to synthesize the audio. For example, you already did that and are testing
debugMode = parseBool(config['SETTINGS']['debug_mode'])

skipTranslation = parseBool(config['SETTINGS']['skip_translation'])  # Set to true if you don't want to translate the subtitles. If so, ignore the following two variables
stopAfterTranslation = parseBool(config['SETTINGS']['stop_after_translation'])

# Note! Setting this to true will make it so instead of just stretching the audio clips, it will have the API generate new audio clips with adjusted speaking rates
# This can't be done on the first pass because we don't know how long the audio clips will be until we generate them
twoPassVoiceSynth = parseBool(config['SETTINGS']['two_pass_voice_synth'])

# Will add this many milliseconds of extra silence before and after each audio clip / spoken subtitle line
addBufferMilliseconds = int(config['SETTINGS']['add_line_buffer_milliseconds'])

#---------------------------------------- Parse Cloud Service Settings ----------------------------------------
# Get auth and project settings for Azure, Google Cloud and/or DeepL
cloudConfig = configparser.ConfigParser()
cloudConfig.read('cloud_service_settings.ini')
tts_service = cloudConfig['CLOUD']['tts_service']

useFallbackGoogleTranslate = parseBool(cloudConfig['CLOUD']['use_fallback_google_translate'])
batchSynthesize = parseBool(cloudConfig['CLOUD']['batch_tts_synthesize'])

#---------------------------------------- Batch File Processing ----------------------------------------

batchConfig = configparser.ConfigParser()
batchConfig.read('batch.ini')
# Get list of languages to process
languageNums = batchConfig['SETTINGS']['enabled_languages'].replace(' ','').split(',')
srtFile = os.path.abspath(batchConfig['SETTINGS']['srt_file_path'].strip("\""))

# Get original video file path, also allow you to debug using a subtitle file without having the original video file
videoFilePath = batchConfig['SETTINGS']['original_video_file_path']
if debugMode and (videoFilePath == '' or videoFilePath.lower() == 'none'):
    originalVideoFile = 'Debug.test'
else:
    originalVideoFile = os.path.abspath(videoFilePath.strip("\""))

# Set output folder based on filename of original video file
outputDirectory = "Outputs"
outputFolder = os.path.join(outputDirectory , os.path.splitext(os.path.basename(originalVideoFile))[0])

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


#======================================== Parse SRT File ================================================
# Open an srt file and read the lines into a list
with open(srtFile, 'r', encoding='utf-8-sig') as f:
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

        # If there are more lines after the subtitle text, add them to the text
        count = 3
        while True:
            # Check if the next line is blank or not
            if (lineNum+count) < len(lines) and lines[lineNum + count].strip():
                lineWithSubtitleText += ' ' + lines[lineNum + count].strip()
                count += 1
            else:
                break

        # Create empty dictionary with keys for start and end times and subtitle text
        subsDict[line] = {'start_ms': '', 'end_ms': '', 'duration_ms': '', 'text': '', 'break_until_next': '', 'srt_timestamps_line': lineWithTimestamps}

        time = lineWithTimestamps.split(' --> ')
        time1 = time[0].split(':')
        time2 = time[1].split(':')

        # Converts the time to milliseconds
        processedTime1 = int(time1[0]) * 3600000 + int(time1[1]) * 60000 + int(time1[2].split(',')[0]) * 1000 + int(time1[2].split(',')[1]) #/ 1000 #Uncomment to turn into seconds
        processedTime2 = int(time2[0]) * 3600000 + int(time2[1]) * 60000 + int(time2[2].split(',')[0]) * 1000 + int(time2[2].split(',')[1]) #/ 1000 #Uncomment to turn into seconds
        timeDifferenceMs = str(processedTime2 - processedTime1)

        # Adjust times with buffer
        if addBufferMilliseconds > 0:
            subsDict[line]['start_ms_buffered'] = str(processedTime1 + addBufferMilliseconds)
            subsDict[line]['end_ms_buffered'] = str(processedTime2 - addBufferMilliseconds)
            subsDict[line]['duration_ms_buffered'] = str((processedTime2 - addBufferMilliseconds) - (processedTime1 + addBufferMilliseconds))
        else:
            subsDict[line]['start_ms_buffered'] = str(processedTime1)
            subsDict[line]['end_ms_buffered'] = str(processedTime2)
            subsDict[line]['duration_ms_buffered'] = str(processedTime2 - processedTime1)
        
        # Set the keys in the dictionary to the values
        subsDict[line]['start_ms'] = str(processedTime1)
        subsDict[line]['end_ms'] = str(processedTime2)
        subsDict[line]['duration_ms'] = timeDifferenceMs
        subsDict[line]['text'] = lineWithSubtitleText
        if lineNum > 0:
            # Goes back to previous line's dictionary and writes difference in time to current line
            subsDict[str(int(line)-1)]['break_until_next'] = processedTime1 - int(subsDict[str(int(line) - 1)]['end_ms'])
        else:
            subsDict[line]['break_until_next'] = 0


# Apply the buffer to the start and end times by setting copying over the buffer values to main values
for key, value in subsDict.items():
    if addBufferMilliseconds > 0:
        subsDict[key]['start_ms'] = value['start_ms_buffered']
        subsDict[key]['end_ms'] = value['end_ms_buffered']
        subsDict[key]['duration_ms'] = value['duration_ms_buffered']


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

# Get the duration of the original video file
if debugMode and originalVideoFile.lower() == "debug.test":
    # Copy the duration based on the last timestamp of the subtitles
    totalAudioLength = int(subsDict[str(len(subsDict))]['end_ms'])
else:
    totalAudioLength = get_duration(originalVideoFile)


#============================================= Directory Validation =====================================================

# Check if the output folder exists, if not, create it
if not os.path.exists(outputDirectory):
    os.makedirs(outputDirectory)
if not os.path.exists(outputFolder):
    os.makedirs(outputFolder)

# Check if the working folder exists, if not, create it
if not os.path.exists('workingFolder'):
    os.makedirs('workingFolder')

#======================================== Translation and Text-To-Speech ================================================    




# Process a language: Translate, Synthesize, and Build Audio
def process_language(langData):
    langDict = {
        'targetLanguage': langData['translation_target_language'], 
        'voiceName': langData['synth_voice_name'], 
        'languageCode': langData['synth_language_code'], 
        'voiceGender': langData['synth_voice_gender'],
        'translateService': langData['translate_service'],
        'formality': langData['formality']
        }

    individualLanguageSubsDict = copy.deepcopy(subsDict)

    # Print language being processed
    print(f"\n----- Beginning Processing of Language: {langDict['languageCode']} -----")

    # Translate
    individualLanguageSubsDict = translate.translate_dictionary(individualLanguageSubsDict, langDict, skipTranslation=skipTranslation)

    if stopAfterTranslation:
        print("Stopping at translation is enabled. Skipping TTS and building audio.")
        return

    # Synthesize
    if batchSynthesize == True and tts_service == 'azure':
        individualLanguageSubsDict = TTS.synthesize_dictionary_batch(individualLanguageSubsDict, langDict, skipSynthesize=skipSynthesize)
    else:
        individualLanguageSubsDict = TTS.synthesize_dictionary(individualLanguageSubsDict, langDict, skipSynthesize=skipSynthesize)

    # Build audio
    individualLanguageSubsDict = audio_builder.build_audio(individualLanguageSubsDict, langDict, totalAudioLength, twoPassVoiceSynth)    



# Process all languages
print(f"\n----- Beginning Processing of Languages -----")
batchSettings = translate.set_translation_info(batchSettings)
for langNum, langData in batchSettings.items():
    # Process current fallback language
    process_language(langData)
