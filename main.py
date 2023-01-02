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
import copy
# Import other modules
import ffprobe
import langcodes

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

# Will add this many milliseconds of extra silence before and after each audio clip / spoken subtitle line
addBufferMilliseconds = int(config['SETTINGS']['add_line_buffer_milliseconds'])

# Will combine subtitles into one audio clip if they are less than this many characters
combineMaxChars = int(config['SETTINGS']['combine_subtitles_max_chars'])  

#---------------------------------------- Parse Cloud Service Settings ----------------------------------------
# Get auth and project settings for Azure or Google Cloud
cloudConfig = configparser.ConfigParser()
cloudConfig.read('cloud_service_settings.ini')
tts_service = cloudConfig['CLOUD']['tts_service']
googleProjectID = cloudConfig['CLOUD']['google_project_id']
batchSynthesize = parseBool(cloudConfig['CLOUD']['batch_tts_synthesize'])

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


# Concatonates text subtitles that start and end at the same time, with maximum of 150 characters
def combine_subtitle_entries(inputDict, maxCharacters=200):
    tempDict = copy.deepcopy(inputDict)
    for key, value in tempDict.items():
        try:
            # Check if combining the current and next subtitle would be within the max characters
            # Automatically handles last entry scenario because the break_until_next value is None, not zero
            if inputDict[key]['break_until_next'] == 0 and len(value['text']+inputDict[str(int(key) + 1)]['text']) < maxCharacters:

                # Combine the text into current entry
                inputDict[key]['text'] = value['text'] + ' ' + inputDict[str(int(key) + 1)]['text']

                # Set the current entry's end time to the next entry's end time
                inputDict[key]['end_ms'] = inputDict[str(int(key) + 1)]['end_ms']
                inputDict[key]['end_ms_buffered'] = inputDict[str(int(key) + 1)]['end_ms_buffered']

                # Combine the current entry's duration with the next entry's duration
                inputDict[key]['duration_ms'] = int(inputDict[key]['duration_ms']) + int(inputDict[str(int(key) + 1)]['duration_ms'])
                # When combining, need to add 2x the buffer to account for the buffer time that was applied between them
                inputDict[key]['duration_ms_buffered'] = int(inputDict[key]['duration_ms_buffered']) + int(inputDict[str(int(key) + 1)]['duration_ms_buffered']) + 2*addBufferMilliseconds

                # Rewrite srt_timestamps_line to include the new end time
                inputDict[key]['srt_timestamps_line'] = inputDict[key]['srt_timestamps_line'].split(' --> ')[0] + ' --> ' + inputDict[str(int(key) + 1)]['srt_timestamps_line'].split(' --> ')[1]

                # Delete the next entry after combining
                del inputDict[str(int(key) + 1)]

        except KeyError as kx:
            # Expect KeyError when trying next entry that has been deleted
            if key == kx.args[0]:
                continue

    return inputDict


#----------------------------------------------------------------------
def combine_subtitles_advanced(inputDict, maxCharacters=200):
    upperCharRateExtreme = 25 #25
    upperCharRate = 22 #22
    lowerCharRate = 18 #18
    lowerCharRateExtreme = 15 #15
    gapThreshold = 100 # The maximum gap between subtitles to combine

    # Convert dictionary to list of dictionaries of the values
    entryList = []
    for key, value in inputDict.items():
        entryList.append(value)
    
    def combine_single_pass(entryListLocal, upper, lower):
        # Want to restart the loop if a change is made, otherwise break only if the end is reached
        reachedEndOfList = False

        while not reachedEndOfList:
            # Need to calculate the char_rate for each entry, any time something changes, so put it at the top of this loop
            entryListLocal = calc_list_speaking_rates(entryListLocal)
            # If the char_rate is outside the upper and lower bounds combine it with either the previous or next entry
            for i, data in enumerate(entryListLocal):
                
                # Check if last entry, and therefore will end loop when done with this iteration
                if i == len(entryListLocal) - 1:
                    reachedEndOfList = True

                # Check if the current entry is outside the upper and lower bounds
                if (data['char_rate'] > upper or data['char_rate'] < lower):

                    # Set flags for whether to consider the next and previous entries
                    considerNext = True
                    considerPrev = True

                    # Get the char_rate of the next and previous entries, if they exist, and calculate the difference
                    # If the diff is positive, then it is lower than the current char_rate
                    try:
                        nextCharRate = entryListLocal[i+1]['char_rate']
                        nextDiff = data['char_rate'] - nextCharRate
                    except IndexError:
                        considerNext = False
                        nextCharRate = None
                        nextDiff = None
                        reachedEndOfList = True
                    try:
                        # If first entry, set values manually. If try to use i-1, will wrap back and use last entry
                        if i == 0:
                            considerPrev = False
                            prevCharRate = None
                            prevDiff = None
                        else:
                            prevCharRate = entryListLocal[i-1]['char_rate']
                            prevDiff = data['char_rate'] - prevCharRate
                    except IndexError:
                        considerPrev = False
                        prevCharRate = None
                        prevDiff = None
                        
                else:
                    continue

                # Define functions for combining with previous or next entries - Generated with coPilot, it's possible this isn't perfectsa
                def combine_with_next():
                    entryListLocal[i]['text'] = entryListLocal[i]['text'] + ' ' + entryListLocal[i+1]['text']
                    entryListLocal[i]['translated_text'] = entryListLocal[i]['translated_text'] + ' ' + entryListLocal[i+1]['translated_text']
                    entryListLocal[i]['end_ms'] = entryListLocal[i+1]['end_ms']
                    entryListLocal[i]['end_ms_buffered'] = entryListLocal[i+1]['end_ms_buffered']
                    entryListLocal[i]['duration_ms'] = int(entryListLocal[i]['duration_ms']) + int(entryListLocal[i+1]['duration_ms'])
                    entryListLocal[i]['duration_ms_buffered'] = str(int(entryListLocal[i]['duration_ms_buffered']) + int(entryListLocal[i+1]['duration_ms_buffered']) + 2*addBufferMilliseconds)
                    entryListLocal[i]['srt_timestamps_line'] = entryListLocal[i]['srt_timestamps_line'].split(' --> ')[0] + ' --> ' + entryListLocal[i+1]['srt_timestamps_line'].split(' --> ')[1]
                    del entryListLocal[i+1]

                def combine_with_prev():
                    entryListLocal[i-1]['text'] = entryListLocal[i-1]['text'] + ' ' + entryListLocal[i]['text']
                    entryListLocal[i-1]['translated_text'] = entryListLocal[i-1]['translated_text'] + ' ' + entryListLocal[i]['translated_text']
                    entryListLocal[i-1]['end_ms'] = entryListLocal[i]['end_ms']
                    entryListLocal[i-1]['end_ms_buffered'] = entryListLocal[i]['end_ms_buffered']
                    entryListLocal[i-1]['duration_ms'] = int(entryListLocal[i-1]['duration_ms']) + int(entryListLocal[i]['duration_ms'])
                    entryListLocal[i-1]['duration_ms_buffered'] = int(entryListLocal[i-1]['duration_ms_buffered']) + int(entryListLocal[i]['duration_ms_buffered']) + 2*addBufferMilliseconds
                    entryListLocal[i-1]['srt_timestamps_line'] = entryListLocal[i-1]['srt_timestamps_line'].split(' --> ')[0] + ' --> ' + entryListLocal[i]['srt_timestamps_line'].split(' --> ')[1]
                    del entryListLocal[i]

                # Choose whether to consider next and previous entries, and if neither then continue to next loop
                if data['char_rate'] > upper:
                    # Check to ensure next/previous rates are lower than current rate, and the combined entry is not too long, and the gap between entries is not too large
                    if not nextDiff or nextDiff < 0 or (entryListLocal[i]['break_until_next'] >= gapThreshold) or (len(entryListLocal[i]['translated_text']) + len(entryListLocal[i+1]['translated_text']) > maxCharacters):
                        considerNext = False
                    if not prevDiff or prevDiff < 0 or (entryListLocal[i-1]['break_until_next'] >= gapThreshold) or (len(entryListLocal[i-1]['translated_text']) + len(entryListLocal[i]['translated_text']) > maxCharacters):
                        considerPrev = False
                elif data['char_rate'] < lower:
                    # Check to ensure next/previous rates are higher than current rate
                    if not nextDiff or nextDiff > 0 or (entryListLocal[i]['break_until_next'] >= gapThreshold) or (len(entryListLocal[i]['translated_text']) + len(entryListLocal[i+1]['translated_text']) > maxCharacters):
                        considerNext = False
                    if not prevDiff or prevDiff > 0 or (entryListLocal[i-1]['break_until_next'] >= gapThreshold) or (len(entryListLocal[i-1]['translated_text']) + len(entryListLocal[i]['translated_text']) > maxCharacters):
                        considerPrev = False
                else:
                    continue

                # Continue to next loop if neither are considered
                if not considerNext and not considerPrev:
                    continue

                # Should only reach this point if two entries are to be combined
                if data['char_rate'] > upper:
                    # If both are to be considered, then choose the one with the lower char_rate
                    if considerNext and considerPrev:
                        if nextDiff < prevDiff:
                            combine_with_next()
                            break
                        else:
                            combine_with_prev()
                    # If only one is to be considered, then combine with that one
                    elif considerNext:
                        combine_with_next()
                    elif considerPrev:
                        combine_with_prev()
                    else:
                        print(f"Error U: Should not reach this point! Current entry = {i}")
                        print(f"Current Entry Text = {data['text']}")
                        continue
                
                elif data['char_rate'] < lower:
                    # If both are to be considered, then choose the one with the higher char_rate
                    if considerNext and considerPrev:
                        if nextDiff > prevDiff:
                            combine_with_next()
                        else:
                            combine_with_prev()
                    # If only one is to be considered, then combine with that one
                    elif considerNext:
                        combine_with_next()
                    elif considerPrev:
                        combine_with_prev()
                    else:
                        print(f"Error L: Should not reach this point! Index = {i}")
                        print(f"Current Entry Text = {data['text']}")
                        continue
        return entryListLocal

    #-- End of combine_single_pass --

    # First will look for extremes to combine, then do another pass to combine the rest
    # Need to create new list variable or else it won't update entryList if that is used for some reason
    entryList2 = combine_single_pass(entryList, upperCharRateExtreme, lowerCharRateExtreme)
    entryList3 = combine_single_pass(entryList2, upperCharRate, lowerCharRate)

    # Convert the list back to a dictionary then return it
    return dict(enumerate(entryList3))

#----------------------------------------------------------------------

# Calculate the number of characters per second for each subtitle entry
def calc_dict_speaking_rates(inputDict, dictKey='translated_text'):  
    tempDict = copy.deepcopy(inputDict)
    for key, value in tempDict.items():
        tempDict[key]['char_rate'] = round(len(value[dictKey]) / (int(value['duration_ms']) / 1000), 2)
    return tempDict

def calc_list_speaking_rates(inputList, dictKey='translated_text'): 
    tempList = copy.deepcopy(inputList)
    for i in range(len(tempList)):
        tempList[i]['char_rate'] = round(len(tempList[i][dictKey]) / (int(tempList[i]['duration_ms']) / 1000), 2)
    return tempList

# Apply the buffer to the start and end times by setting copying over the buffer values to main values
for key, value in subsDict.items():
    if addBufferMilliseconds > 0:
        subsDict[key]['start_ms'] = value['start_ms_buffered']
        subsDict[key]['end_ms'] = value['end_ms_buffered']
        subsDict[key]['duration_ms'] = value['duration_ms_buffered']

#======================================== Translate Text ================================================
# Note: This function was almost entirely written by GPT-3 after feeding it my original code and asking it to change it so it
# would break up the text into chunks if it was too long. It appears to work

# Translate the text entries of the dictionary
def translate_dictionary(inputSubsDict, langDict, skipTranslation=False):
    targetLanguage = langDict['targetLanguage']

    # Create a container for all the text to be translated
    textToTranslate = []

    for key in inputSubsDict:
        originalText = inputSubsDict[key]['text']
        textToTranslate.append(originalText)
    
    # Calculate the total number of utf-8 codepoints
    codepoints = 0
    for text in textToTranslate:
        codepoints += len(text.encode("utf-8"))
    
    # If the codepoints are greater than 28000, split the request into multiple
    # Google's API limit is 30000 Utf-8 codepoints per request, but we leave some room just in case
    if skipTranslation == False:
        if codepoints > 27000:
            # GPT-3 Description of what the following line does:
            # Splits the list of text to be translated into smaller chunks of 100 texts.
            # It does this by looping over the list in steps of 100, and slicing out each chunk from the original list. 
            # Each chunk is appended to a new list, chunkedTexts, which then contains the text to be translated in chunks.
            chunkedTexts = [textToTranslate[x:x+100] for x in range(0, len(textToTranslate), 100)]
            
            # Send and receive the batch requests
            for chunk in chunkedTexts:
                # Print status with progress
                print(f'Translating text group {chunkedTexts.index(chunk)+1} of {len(chunkedTexts)}')
                
                # Send the request
                response = auth.TRANSLATE_API.projects().translateText(
                    parent='projects/' + googleProjectID,
                    body={
                        'contents': chunk,
                        'sourceLanguageCode': originalLanguage,
                        'targetLanguageCode': targetLanguage,
                        'mimeType': 'text/plain',
                        #'model': 'nmt',
                        #'glossaryConfig': {}
                    }
                ).execute()
                
                # Extract the translated texts from the response
                translatedTexts = [response['translations'][i]['translatedText'] for i in range(len(response['translations']))]
                
                # Add the translated texts to the dictionary
                for i, key in enumerate(inputSubsDict):
                    inputSubsDict[key]['translated_text'] = translatedTexts[i]
                    # Print progress, ovwerwrite the same line
                    print(f' Translated: {key} of {len(inputSubsDict)}', end='\r')
        
        else:
            print("Translating text...")
            response = auth.TRANSLATE_API.projects().translateText(
                parent='projects/' + googleProjectID,
                body={
                    'contents':textToTranslate,
                    'sourceLanguageCode': originalLanguage,
                    'targetLanguageCode': targetLanguage,
                    'mimeType': 'text/plain',
                    #'model': 'nmt',
                    #'glossaryConfig': {}
                }
            ).execute()
            translatedTexts = [response['translations'][i]['translatedText'] for i in range(len(response['translations']))]
            for i, key in enumerate(inputSubsDict):
                inputSubsDict[key]['translated_text'] = translatedTexts[i]
                # Print progress, ovwerwrite the same line
                print(f' Translated: {key} of {len(inputSubsDict)}', end='\r')
    else:
        for key in inputSubsDict:
            inputSubsDict[key]['translated_text'] = inputSubsDict[key]['text'] # Skips translating, such as for testing
    print("                                                  ")

    combinedProcessedDict = combine_subtitles_advanced(inputSubsDict, combineMaxChars)

    if skipTranslation == False:
        # Use video file name to use in the name of the translate srt file, also display regular language name
        lang = langcodes.get(targetLanguage).display_name()
        translatedSrtFileName = pathlib.Path(originalVideoFile).stem + f" - {lang} - {targetLanguage}.srt"
        # Set path to save translated srt file
        translatedSrtFileName = os.path.join(outputFolder, translatedSrtFileName)
        # Write new srt file with translated text
        with open(translatedSrtFileName, 'w', encoding='utf-8') as f:
            for key in combinedProcessedDict:
                f.write(key + '\n')
                f.write(combinedProcessedDict[key]['srt_timestamps_line'] + '\n')
                f.write(combinedProcessedDict[key]['translated_text'] + '\n\n')

    return combinedProcessedDict

#============================================= Directory Validation =====================================================

# Check if the output folder exists, if not, create it
if not os.path.exists(outputFolder):
    os.makedirs(outputFolder)

# Check if the working folder exists, if not, create it
if not os.path.exists('workingFolder'):
    os.makedirs('workingFolder')

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
    individualLanguageSubsDict = copy.deepcopy(subsDict)

    # Print language being processed
    print(f"\n----- Beginning Processing of Language: {langDict['languageCode']} -----")

    # Translate
    individualLanguageSubsDict = translate_dictionary(individualLanguageSubsDict, langDict, skipTranslation=skipTranslation)

    # Synthesize
    if batchSynthesize == True and tts_service == 'azure':
        individualLanguageSubsDict = TTS.synthesize_dictionary_batch(individualLanguageSubsDict, langDict, skipSynthesize=skipSynthesize)
    else:
        individualLanguageSubsDict = TTS.synthesize_dictionary(individualLanguageSubsDict, langDict, skipSynthesize=skipSynthesize)

    # Build audio
    individualLanguageSubsDict = audio_builder.build_audio(individualLanguageSubsDict, langDict, totalAudioLength, twoPassVoiceSynth)
