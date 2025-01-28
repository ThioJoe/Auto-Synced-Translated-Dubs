#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Project Title: Auto Synced Translated Dubs (https://github.com/ThioJoe/Auto-Synced-Translated-Dubs)
# Author / Project Owner: "ThioJoe" (https://github.com/ThioJoe)
# License: GPLv3
# NOTE: By contributing to this project, you agree to the terms of the GPLv3 license, and agree to grant the project owner the right to also provide or sell this software, including your contribution, to anyone under any other license, with no compensation to you.

version = '0.21.0'
print(f"------- 'Auto Synced Translated Dubs' script by ThioJoe - Release version {version} -------")

# Import other files
from Scripts.shared_imports import *
import Scripts.TTS as TTS
import Scripts.audio_builder as audio_builder
import Scripts.auth as auth
import Scripts.translate as translate

# Import built in modules
import re
import copy
import asyncio
# Import winsound if on Windows
if os.name == 'nt':
    import winsound

# Import other modules
import ffprobe

# EXTERNAL REQUIREMENTS:
# rubberband binaries: https://breakfastquay.com/rubberband/ - Put rubberband.exe and sndfile.dll in the same folder as this script
# ffmpeg installed: https://ffmpeg.org/download.html



#---------------------------------------- Batch File Processing ----------------------------------------

# Get list of languages to process
languageNums = batchConfig['SETTINGS']['enabled_languages'].replace(' ','').split(',')
srtFile = os.path.abspath(batchConfig['SETTINGS']['srt_file_path'].strip("\""))

# Get original video file path, also allow you to debug using a subtitle file without having the original video file
videoFilePath = batchConfig['SETTINGS']['original_video_file_path']

# Validate the number of sections
for num in languageNums:
    # Check if section exists
    if not batchConfig.has_section(f'LANGUAGE-{num}'):
        raise ValueError(f'Invalid language number in batch.ini: {num} - Make sure the section [LANGUAGE-{num}] exists')

# Validate the settings in each batch section
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

    # Set voice model if applicable (different from voice name, only used by some services)
    if not batchConfig.has_option(f'LANGUAGE-{num}', 'model'):
        model = "default"
    else:
        model = batchConfig[f'LANGUAGE-{num}']['model']
        
    if not batchConfig.has_option(f'LANGUAGE-{num}', 'synth_voice_style') or batchConfig[f'LANGUAGE-{num}']['synth_voice_style'] == "":
        style = "default"
    else:
        style = batchConfig[f'LANGUAGE-{num}']['synth_voice_style']
        
    if cloudConfig.tts_service == 'elevenlabs':
        if model == "default":
            model = cloudConfig.elevenlabs_default_model
    else:
        model = "default"

    # Set the dictionary values for each language
    batchSettings[num] = {
        'synth_language_code': batchConfig[f'LANGUAGE-{num}']['synth_language_code'],
        'synth_voice_name': batchConfig[f'LANGUAGE-{num}']['synth_voice_name'],
        'translation_target_language': batchConfig[f'LANGUAGE-{num}'][LangDataKeys.translation_target_language],
        'synth_voice_gender': batchConfig[f'LANGUAGE-{num}']['synth_voice_gender'],
        'synth_voice_model': model,
        'synth_voice_style': style,
    }


#======================================== Parse SRT File ================================================

def parse_srt_file(srtFileLines, preTranslated=False):
    # Matches the following example with regex:    00:00:20,130 --> 00:00:23,419
    subtitleTimeLineRegex = re.compile(r'\d\d:\d\d:\d\d,\d\d\d --> \d\d:\d\d:\d\d,\d\d\d')

    # Create a dictionary
    subsDict = {}

    # Will add this many milliseconds of extra silence before and after each audio clip / spoken subtitle line
    addBufferMilliseconds = int(config.add_line_buffer_milliseconds)

    # Enumerate lines, and if a line in lines contains only an integer, put that number in the key, and a dictionary in the value
    # The dictionary contains the start, ending, and duration of the subtitles as well as the text
    # The next line uses the syntax HH:MM:SS,MMM --> HH:MM:SS,MMM . Get the difference between the two times and put that in the dictionary
    # For the line after that, put the text in the dictionary
    for lineNum, line in enumerate(srtFileLines):
        line = line.strip()
        if line.isdigit() and subtitleTimeLineRegex.match(srtFileLines[lineNum + 1]):
            lineWithTimestamps = srtFileLines[lineNum + 1].strip()
            lineWithSubtitleText = srtFileLines[lineNum + 2].strip()

            # If there are more lines after the subtitle text, add them to the text
            count = 3
            while True:
                # Check if the next line is blank or not
                if (lineNum+count) < len(srtFileLines) and srtFileLines[lineNum + count].strip():
                    lineWithSubtitleText += ' ' + srtFileLines[lineNum + count].strip()
                    count += 1
                else:
                    break

            # Create empty dictionary with keys for start and end times and subtitle text
            subsDict[line] = {SubsDictKeys.start_ms: '', SubsDictKeys.end_ms: '', SubsDictKeys.duration_ms: '', SubsDictKeys.text: '', SubsDictKeys.break_until_next: '', SubsDictKeys.srt_timestamps_line: lineWithTimestamps}

            time = lineWithTimestamps.split(' --> ')
            time1 = time[0].split(':')
            time2 = time[1].split(':')

            # Converts the time to milliseconds
            processedTime1 = int(time1[0]) * 3600000 + int(time1[1]) * 60000 + int(time1[2].split(',')[0]) * 1000 + int(time1[2].split(',')[1]) #/ 1000 #Uncomment to turn into seconds
            processedTime2 = int(time2[0]) * 3600000 + int(time2[1]) * 60000 + int(time2[2].split(',')[0]) * 1000 + int(time2[2].split(',')[1]) #/ 1000 #Uncomment to turn into seconds
            timeDifferenceMs = str(processedTime2 - processedTime1)

            # Adjust times with buffer
            if addBufferMilliseconds > 0 and not preTranslated:
                subsDict[line][SubsDictKeys.start_ms_buffered] = str(processedTime1 + addBufferMilliseconds)
                subsDict[line][SubsDictKeys.end_ms_buffered] = str(processedTime2 - addBufferMilliseconds)
                subsDict[line][SubsDictKeys.duration_ms_buffered] = str((processedTime2 - addBufferMilliseconds) - (processedTime1 + addBufferMilliseconds))
            else:
                subsDict[line][SubsDictKeys.start_ms_buffered] = str(processedTime1)
                subsDict[line][SubsDictKeys.end_ms_buffered] = str(processedTime2)
                subsDict[line][SubsDictKeys.duration_ms_buffered] = str(processedTime2 - processedTime1)
            
            # Set the keys in the dictionary to the values
            subsDict[line][SubsDictKeys.start_ms] = str(processedTime1)
            subsDict[line][SubsDictKeys.end_ms] = str(processedTime2)
            subsDict[line][SubsDictKeys.duration_ms] = timeDifferenceMs
            subsDict[line][SubsDictKeys.text] = lineWithSubtitleText
            if lineNum > 0:
                # Goes back to previous line's dictionary and writes difference in time to current line
                subsDict[str(int(line)-1)][SubsDictKeys.break_until_next] = processedTime1 - int(subsDict[str(int(line) - 1)][SubsDictKeys.end_ms])
            else:
                subsDict[line][SubsDictKeys.break_until_next] = 0


    # Apply the buffer to the start and end times by setting copying over the buffer values to main values
    if addBufferMilliseconds > 0 and not preTranslated:
        for key, value in subsDict.items():
            subsDict[key][SubsDictKeys.start_ms] = value[SubsDictKeys.start_ms_buffered]
            subsDict[key][SubsDictKeys.end_ms] = value[SubsDictKeys.end_ms_buffered]
            subsDict[key][SubsDictKeys.duration_ms] = value[SubsDictKeys.duration_ms_buffered]

    return subsDict

# ----------------------------------------

# Open an srt file and read the lines into a list
with open(srtFile, 'r', encoding='utf-8-sig') as f:
    originalSubLines = f.readlines()

originalLanguageSubsDict = parse_srt_file(originalSubLines)

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
if config.debug_mode and ORIGINAL_VIDEO_PATH.lower() == "debug.test":
    # Copy the duration based on the last timestamp of the subtitles
    totalAudioLength = int(originalLanguageSubsDict[str(len(originalLanguageSubsDict))][SubsDictKeys.end_ms])
else:
    totalAudioLength = get_duration(ORIGINAL_VIDEO_PATH)


#============================================= Directory Validation =====================================================

# Check if the output folder exists, if not, create it
if not os.path.exists(OUTPUT_DIRECTORY):
    os.makedirs(OUTPUT_DIRECTORY)
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

# Check if the working folder exists, if not, create it
if not os.path.exists('workingFolder'):
    os.makedirs('workingFolder')

#======================================== Translation and Text-To-Speech ================================================

def manually_prepare_dictionary(dictionaryToPrep):
    ### Do additional Processing to match the format produced by translation function
    # Create new key 'translated_text' and set it to the value of 'text'
    for key, value in dictionaryToPrep.items():
        dictionaryToPrep[key][SubsDictKeys.translated_text] = value[SubsDictKeys.text]
    
    # Convert the keys to integers and return the dictionary
    return {int(k): v for k, v in dictionaryToPrep.items()}

def get_pretranslated_subs_dict(langData):
    # Get list of files in the output folder
    files = os.listdir(OUTPUT_FOLDER)
    # Check if youtube-translated directory/files exist
    if os.path.exists(OUTPUT_YTSYNCED_FOLDER):
        altFiles = os.listdir(OUTPUT_YTSYNCED_FOLDER)
    else:
        altFiles = None
    
    # If alternative translations found in addition to the main output folder, ask user which to use
    if altFiles and files:
        print("Found YouTube-synced translations in: " + OUTPUT_YTSYNCED_FOLDER)
        userResponse = input("Use YouTube-synced translations instead of those in main output folder? (y/n): ")
        if userResponse.lower() == 'y':
            files = altFiles
            print("Using YouTube-synced translations...\n")
    elif altFiles and not files:
        print("Found YouTube-synced translations to use in: " + OUTPUT_YTSYNCED_FOLDER)
        files = altFiles
    
    # Check if any files ends with the specific language code and srt file extension
    for file in files:
        if file.replace(' ', '').endswith(f"-{langData[LangDataKeys.translation_target_language]}.srt"):
            # If so, open the file and read the lines into a list
            with open(f"{OUTPUT_FOLDER}/{file}", 'r', encoding='utf-8-sig') as f:
                pretranslatedSubLines = f.readlines()
            print(f"Pre-translated file found: {file}")

            # Parse the srt file using function
            preTranslatedDict = parse_srt_file(pretranslatedSubLines, preTranslated=True)

            # Convert the keys to integers
            preTranslatedDict = manually_prepare_dictionary(preTranslatedDict)

            # Return the dictionary
            return preTranslatedDict
        
    # If no file is found, return None
    return None

# Process a language: Translate, Synthesize, and Build Audio
def process_language(langData, processedCount, totalLanguages):
    langDict = {
        LangDictKeys.targetLanguage: langData[LangDataKeys.translation_target_language], 
        LangDictKeys.voiceName: langData[LangDataKeys.synth_voice_name], 
        LangDictKeys.languageCode: langData[LangDataKeys.synth_language_code], 
        LangDictKeys.voiceGender: langData[LangDataKeys.synth_voice_gender],
        LangDictKeys.translateService: langData[LangDataKeys.translate_service],
        LangDictKeys.formality: langData[LangDataKeys.formality],
        LangDictKeys.voiceModel: langData[LangDataKeys.synth_voice_model],
        LangDictKeys.voiceStyle: langData[LangDataKeys.synth_voice_style]
    }

    individualLanguageSubsDict = copy.deepcopy(originalLanguageSubsDict)

    # Print language being processed
    print(f"\n----- Beginning Processing of Language ({processedCount}/{totalLanguages}): {langDict[LangDictKeys.languageCode]} -----")

    # Check for special case where original language is the same as the target language
    if langDict[LangDictKeys.languageCode].lower() == config.original_language.lower():
        print("Original language is the same as the target language. Skipping translation.")
        # individualLanguageSubsDict = manually_prepare_dictionary(individualLanguageSubsDict)
        # Runs through translation function and skips translation process, but still combines subtitles and prints srt file for native language
        individualLanguageSubsDict = translate.translate_dictionary(individualLanguageSubsDict, langDict, skipTranslation=True, forceNativeSRTOutput=True)

    elif config.skip_translation == False:
        # Translate
        individualLanguageSubsDict = translate.translate_dictionary(individualLanguageSubsDict, langDict, skipTranslation=config.skip_translation)
        if config.stop_after_translation:
            print("Stopping at translation is enabled. Skipping TTS and building audio.")
            return
        
    elif config.skip_translation == True:
        print("Skip translation enabled. Checking for pre-translated subtitles...")
        # Check if pre-translated subtitles exist
        pretranslatedSubsDict = get_pretranslated_subs_dict(langData)
        if pretranslatedSubsDict != None:
            individualLanguageSubsDict = pretranslatedSubsDict
        else:
            print(f"\nPre-translated subtitles not found for language '{langDict[LangDictKeys.languageCode]}' in folder '{OUTPUT_FOLDER}'. Skipping.")
            print(f"Note: Ensure the subtitle filename for this language ends with: ' - {langData[LangDataKeys.translation_target_language]}.srt'\n")
            return

    # Synthesize
    if cloudConfig.batch_tts_synthesize == True and cloudConfig.tts_service == TTSService.AZURE:
        individualLanguageSubsDict = TTS.synthesize_dictionary_batch(individualLanguageSubsDict, langDict, skipSynthesize=config.skip_synthesize)
    elif cloudConfig.tts_service == 'elevenlabs':
        individualLanguageSubsDict = asyncio.run(TTS.synthesize_dictionary_async(individualLanguageSubsDict, langDict, skipSynthesize=config.skip_synthesize, max_concurrent_jobs=cloudConfig.elevenlabs_max_concurrent))
    else:
        individualLanguageSubsDict = TTS.synthesize_dictionary(individualLanguageSubsDict, langDict, skipSynthesize=config.skip_synthesize)

    # Build audio
    individualLanguageSubsDict = audio_builder.build_audio(individualLanguageSubsDict, langDict, totalAudioLength, config.two_pass_voice_synth)    


#======================================== Main Program ================================================
# Set asyncio event loop policy to WindowsSelectorEventLoopPolicy if on Windows to avoid errors
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Counter for number of languages processed
processedCount = 0
totalLanguages = len(batchSettings)

# Process all languages
print(f"\n----- Beginning Processing of Languages -----")
batchSettings = translate.set_translation_info(batchSettings)
for langNum, langData in batchSettings.items():
    processedCount += 1
    # Process current fallback language
    process_language(langData, processedCount, totalLanguages)

# Play a system sound to indicate completion
if os.name == 'nt':
    sound_name = winsound.MB_ICONASTERISK  # represents the 'Asterisk' system sound
    winsound.MessageBeep(sound_name)  # Play the system sound
