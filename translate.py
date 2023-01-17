#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Imports
import auth
from utils import parseBool

import configparser
from operator import itemgetter
import sys
import copy
import os
import pathlib
import langcodes

# Get Configs
cloudConfig = configparser.ConfigParser()
cloudConfig.read('cloud_service_settings.ini')
config = configparser.ConfigParser()
config.read('config.ini')
batchConfig = configparser.ConfigParser()
batchConfig.read('batch.ini')

# Get settings from configs
googleProjectID = cloudConfig['CLOUD']['google_project_id']

# Translation Settings
originalLanguage = config['SETTINGS']['original_language']
formalityPreference = config['SETTINGS']['formality_preference']
preferredTranslateService = cloudConfig['CLOUD']['translate_service']
debugMode = parseBool(config['SETTINGS']['debug_mode'])
combineMaxChars = int(config['SETTINGS']['combine_subtitles_max_chars']) # Will combine subtitles into one audio clip if they are less than this many characters

# MOVE THESE INTO A DICTIONARY VARIABLE AT SOME POINT
outputFolder = "output"
originalVideoFile = os.path.abspath(batchConfig['SETTINGS']['original_video_file_path'].strip("\""))

#======================================== Translate Text ================================================
# Note: This function was almost entirely written by GPT-3 after feeding it my original code and asking it to change it so it
# would break up the text into chunks if it was too long. It appears to work

# Translate the text entries of the dictionary
def translate_dictionary(inputSubsDict, langDict, skipTranslation=False):
    targetLanguage = langDict['targetLanguage']
    translateService = langDict['translateService']
    formality = langDict['formality']

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
    # Google's API limit is 30000 Utf-8 codepoints per request, while DeepL's is 130000, but we leave some room just in case
    if skipTranslation == False:
        if translateService == 'google' and codepoints > 27000 or translateService == 'deepl' and codepoints > 120000:
            # GPT-3 Description of what the following line does:
            # If Google Translate is being used:
            # Splits the list of text to be translated into smaller chunks of 100 texts.
            # It does this by looping over the list in steps of 100, and slicing out each chunk from the original list. 
            # Each chunk is appended to a new list, chunkedTexts, which then contains the text to be translated in chunks.
            # The same thing is done for DeepL, but the chunk size is 400 instead of 100.
            chunkSize = 100 if translateService == 'google' else 400
            chunkedTexts = [textToTranslate[x:x+chunkSize] for x in range(0, len(textToTranslate), chunkSize)]
            
            # Send and receive the batch requests
            for j,chunk in enumerate(chunkedTexts):
                
                # Send the request
                if translateService == 'google':
                    # Print status with progress
                    print(f'[Google] Translating text group {j+1} of {len(chunkedTexts)}')
                    response = auth.GOOGLE_TRANSLATE_API.projects().translateText(
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
                    # Divide the dictionary into chunks of 100
                    for i in range(chunkSize):
                        key = str((i+1+j*chunkSize))
                        inputSubsDict[key]['translated_text'] = translatedTexts[i]
                        # Print progress, ovwerwrite the same line
                        print(f' Translated with Google: {key} of {len(inputSubsDict)}', end='\r')

                elif translateService == 'deepl':
                    print(f'[DeepL] Translating text group {j+1} of {len(chunkedTexts)}')

                    # Send the request
                    result = auth.DEEPL_API.translate_text(chunk, target_lang=targetLanguage, formality=formality)
                    
                    # Extract the translated texts from the response
                    translatedTexts = [result[i].text for i in range(len(result))]

                    # Add the translated texts to the dictionary
                    for i in range(chunkSize):
                        key = str((i+1+j*chunkSize))
                        inputSubsDict[key]['translated_text'] = translatedTexts[i]
                        # Print progress, ovwerwrite the same line
                        print(f' Translated with DeepL: {key} of {len(inputSubsDict)}', end='\r')
                else:
                    print("Error: Invalid translate_service setting. Only 'google' and 'deepl' are supported.")
                    sys.exit()
                
        else:
            if translateService == 'google':
                print("Translating text using Google...")
                response = auth.GOOGLE_TRANSLATE_API.projects().translateText(
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
                
                # Add the translated texts to the dictionary
                for i, key in enumerate(inputSubsDict):
                    inputSubsDict[key]['translated_text'] = translatedTexts[i]
                    # Print progress, overwrite the same line
                    print(f' Translated: {key} of {len(inputSubsDict)}', end='\r')

            elif translateService == 'deepl':
                print("Translating text using DeepL...")

                # Send the request
                result = auth.DEEPL_API.translate_text(textToTranslate, target_lang=targetLanguage, formality=formality)

                # Add the translated texts to the dictionary
                for i, key in enumerate(inputSubsDict):
                    inputSubsDict[key]['translated_text'] = result[i].text
                    # Print progress, overwrite the same line
                    print(f' Translated: {key} of {len(inputSubsDict)}', end='\r')
            else:
                print("Error: Invalid translate_service setting. Only 'google' and 'deepl' are supported.")
                sys.exit()
    else:
        for key in inputSubsDict:
            inputSubsDict[key]['translated_text'] = inputSubsDict[key]['text'] # Skips translating, such as for testing
    print("                                                  ")

    combinedProcessedDict = combine_subtitles_advanced(inputSubsDict, combineMaxChars)

    if skipTranslation == False or debugMode == True:
        # Use video file name to use in the name of the translate srt file, also display regular language name
        lang = langcodes.get(targetLanguage).display_name()
        if debugMode:
            translatedSrtFileName = pathlib.Path(originalVideoFile).stem + f" - {lang} - {targetLanguage}.DEBUG.txt"
        else:
            translatedSrtFileName = pathlib.Path(originalVideoFile).stem + f" - {lang} - {targetLanguage}.srt"
        # Set path to save translated srt file
        translatedSrtFileName = os.path.join(outputFolder, translatedSrtFileName)
        # Write new srt file with translated text
        with open(translatedSrtFileName, 'w', encoding='utf-8-sig') as f:
            for key in combinedProcessedDict:
                f.write(str(key) + '\n')
                f.write(combinedProcessedDict[key]['srt_timestamps_line'] + '\n')
                f.write(combinedProcessedDict[key]['translated_text'] + '\n')
                if debugMode:
                    f.write(f"DEBUG: duration_ms = {combinedProcessedDict[key]['duration_ms']}" + '\n')
                    f.write(f"DEBUG: char_rate = {combinedProcessedDict[key]['char_rate']}" + '\n')
                    f.write(f"DEBUG: start_ms = {combinedProcessedDict[key]['start_ms']}" + '\n')
                    f.write(f"DEBUG: end_ms = {combinedProcessedDict[key]['end_ms']}" + '\n')
                    f.write(f"DEBUG: start_ms_buffered = {combinedProcessedDict[key]['start_ms_buffered']}" + '\n')
                    f.write(f"DEBUG: end_ms_buffered = {combinedProcessedDict[key]['end_ms_buffered']}" + '\n')
                f.write('\n')

    return combinedProcessedDict


##### Add additional info to the dictionary for each language #####
def set_translation_info(languageBatchDict):
    newBatchSettingsDict = copy.deepcopy(languageBatchDict)

    # Set the translation service for each language
    if preferredTranslateService == 'deepl':
        langSupportResponse = auth.DEEPL_API.get_target_languages()
        supportedLanguagesList = list(map(lambda x: str(x.code).upper(), langSupportResponse))

        # # Create dictionary from response
        # supportedLanguagesDict = {}
        # for lang in langSupportResponse:
        #     supportedLanguagesDict[lang.code.upper()] = {'name': lang.name, 'supports_formality': lang.supports_formality}

        # Fix language codes for certain languages when using DeepL to be region specific
        deepL_code_override = {
            'EN': 'EN-US',
            'PT': 'PT-BR'
        }

        # Set translation service to DeepL if possible and get formality setting, otherwise set to Google
        for langNum, langInfo in languageBatchDict.items():
            # Get language code
            lang = langInfo['translation_target_language'].upper()
            # Check if language is supported by DeepL, or override if needed
            if lang in supportedLanguagesList or lang in deepL_code_override:
                # Fix certain language codes
                if lang in deepL_code_override:
                    newBatchSettingsDict[langNum]['translation_target_language'] = deepL_code_override[lang]
                    lang = deepL_code_override[lang]
                # Set translation service to DeepL
                newBatchSettingsDict[langNum]['translate_service'] = 'deepl'
                # Setting to 'prefer_more' or 'prefer_less' will it will default to 'default' if formality not supported             
                if formalityPreference == 'more':
                    newBatchSettingsDict[langNum]['formality'] = 'prefer_more'
                elif formalityPreference == 'less':
                    newBatchSettingsDict[langNum]['formality'] = 'prefer_less'
                else:
                    # Set formality to None if not supported for that language
                    newBatchSettingsDict[langNum]['formality'] = 'default'

            # If language is not supported, add dictionary entry to use Google
            else:
                newBatchSettingsDict[langNum]['translate_service'] = 'google'
                newBatchSettingsDict[langNum]['formality'] = None
    
    # If using Google, set all languages to use Google in dictionary
    elif preferredTranslateService == 'google':
        for langNum, langInfo in languageBatchDict.items():
            newBatchSettingsDict[langNum]['translate_service'] = 'google'
            newBatchSettingsDict[langNum]['formality'] = None

    return newBatchSettingsDict    


#======================================== Combine Subtitle Lines ================================================
def combine_subtitles_advanced(inputDict, maxCharacters=200):
    charRateGoal = 20 #20
    gapThreshold = 100 # The maximum gap between subtitles to combine

    # Convert dictionary to list of dictionaries of the values
    entryList = []
    for key, value in inputDict.items():
        value['originalIndex'] = int(key)-1
        entryList.append(value)
    
    def combine_single_pass(entryListLocal):
        # Want to restart the loop if a change is made, so use this variable, otherwise break only if the end is reached
        reachedEndOfList = False

        # Use while loop because the list is being modified
        while not reachedEndOfList:
            # Need to calculate the char_rate for each entry, any time something changes, so put it at the top of this loop
            entryListLocal = calc_list_speaking_rates(entryListLocal, charRateGoal)

            # Sort the list by the difference in speaking speed from charRateGoal
            priorityOrderedList = sorted(entryListLocal, key=itemgetter('char_rate_diff'), reverse=True) 

            # Iterates through the list in order of priority, and uses that index to operate on entryListLocal
            # For loop is broken after a combination is made, so that the list can be re-sorted and re-iterated
            for i, data in enumerate(priorityOrderedList):

                # Check if last entry, and therefore will end loop when done with this iteration
                if i == len(priorityOrderedList) - 1:
                    reachedEndOfList = True

                # Check if the current entry is outside the upper and lower bounds
                if (data['char_rate'] > charRateGoal or data['char_rate'] < charRateGoal):

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
                        prevCharRate = entryListLocal[i-1]['char_rate']
                        prevDiff = data['char_rate'] - prevCharRate
                    except IndexError:
                        considerPrev = False
                        prevCharRate = None
                        prevDiff = None
                        
                else:
                    continue

                # Define functions for combining with previous or next entries - Generated with copilot, it's possible this isn't perfect
                def combine_with_next():
                    entryListLocal[i]['text'] = entryListLocal[i]['text'] + ' ' + entryListLocal[i+1]['text']
                    entryListLocal[i]['translated_text'] = entryListLocal[i]['translated_text'] + ' ' + entryListLocal[i+1]['translated_text']
                    entryListLocal[i]['end_ms'] = entryListLocal[i+1]['end_ms']
                    entryListLocal[i]['end_ms_buffered'] = entryListLocal[i+1]['end_ms_buffered']
                    entryListLocal[i]['duration_ms'] = int(entryListLocal[i+1]['end_ms']) - int(entryListLocal[i]['start_ms'])
                    entryListLocal[i]['duration_ms_buffered'] = int(entryListLocal[i+1]['end_ms_buffered']) - int(entryListLocal[i]['start_ms_buffered'])
                    entryListLocal[i]['srt_timestamps_line'] = entryListLocal[i]['srt_timestamps_line'].split(' --> ')[0] + ' --> ' + entryListLocal[i+1]['srt_timestamps_line'].split(' --> ')[1]
                    del entryListLocal[i+1]

                def combine_with_prev():
                    entryListLocal[i-1]['text'] = entryListLocal[i-1]['text'] + ' ' + entryListLocal[i]['text']
                    entryListLocal[i-1]['translated_text'] = entryListLocal[i-1]['translated_text'] + ' ' + entryListLocal[i]['translated_text']
                    entryListLocal[i-1]['end_ms'] = entryListLocal[i]['end_ms']
                    entryListLocal[i-1]['end_ms_buffered'] = entryListLocal[i]['end_ms_buffered']
                    entryListLocal[i-1]['duration_ms'] = int(entryListLocal[i]['end_ms']) - int(entryListLocal[i-1]['start_ms'])
                    entryListLocal[i-1]['duration_ms_buffered'] = int(entryListLocal[i]['end_ms_buffered']) - int(entryListLocal[i-1]['start_ms_buffered'])
                    entryListLocal[i-1]['srt_timestamps_line'] = entryListLocal[i-1]['srt_timestamps_line'].split(' --> ')[0] + ' --> ' + entryListLocal[i]['srt_timestamps_line'].split(' --> ')[1]
                    del entryListLocal[i]


                # Choose whether to consider next and previous entries, and if neither then continue to next loop
                if data['char_rate'] > charRateGoal:
                    # Check to ensure next/previous rates are lower than current rate, and the combined entry is not too long, and the gap between entries is not too large
                    if not nextDiff or nextDiff < 0 or (entryListLocal[i]['break_until_next'] >= gapThreshold) or (len(entryListLocal[i]['translated_text']) + len(entryListLocal[i+1]['translated_text']) > maxCharacters):
                        considerNext = False
                    try:
                        if not prevDiff or prevDiff < 0 or (entryListLocal[i-1]['break_until_next'] >= gapThreshold) or (len(entryListLocal[i-1]['translated_text']) + len(entryListLocal[i]['translated_text']) > maxCharacters):
                            considerPrev = False
                    except TypeError:
                        considerPrev = False

                elif data['char_rate'] < charRateGoal:
                    # Check to ensure next/previous rates are higher than current rate
                    if not nextDiff or nextDiff > 0 or (entryListLocal[i]['break_until_next'] >= gapThreshold) or (len(entryListLocal[i]['translated_text']) + len(entryListLocal[i+1]['translated_text']) > maxCharacters):
                        considerNext = False
                    try:
                        if not prevDiff or prevDiff > 0 or (entryListLocal[i-1]['break_until_next'] >= gapThreshold) or (len(entryListLocal[i-1]['translated_text']) + len(entryListLocal[i]['translated_text']) > maxCharacters):
                            considerPrev = False
                    except TypeError:
                        considerPrev = False
                else:
                    continue

                # Continue to next loop if neither are considered
                if not considerNext and not considerPrev:
                    continue

                # Should only reach this point if two entries are to be combined
                if data['char_rate'] > charRateGoal:
                    # If both are to be considered, then choose the one with the lower char_rate
                    if considerNext and considerPrev:
                        if nextDiff < prevDiff:
                            combine_with_next()
                            break
                        else:
                            combine_with_prev()
                            break
                    # If only one is to be considered, then combine with that one
                    elif considerNext:
                        combine_with_next()
                        break
                    elif considerPrev:
                        combine_with_prev()
                        break
                    else:
                        print(f"Error U: Should not reach this point! Current entry = {i}")
                        print(f"Current Entry Text = {data['text']}")
                        continue
                
                elif data['char_rate'] < charRateGoal:
                    # If both are to be considered, then choose the one with the higher char_rate
                    if considerNext and considerPrev:
                        if nextDiff > prevDiff:
                            combine_with_next()
                            break
                        else:
                            combine_with_prev()
                            break
                    # If only one is to be considered, then combine with that one
                    elif considerNext:
                        combine_with_next()
                        break
                    elif considerPrev:
                        combine_with_prev()
                        break
                    else:
                        print(f"Error L: Should not reach this point! Index = {i}")
                        print(f"Current Entry Text = {data['text']}")
                        continue
        return entryListLocal

    #-- End of combine_single_pass --

    # Two passes since they're combined sequentially in pairs. Might add a better way in the future
    # Need to create new list variable or else it won't update entryList if that is used for some reason
    entryList2 = combine_single_pass(entryList)
    entryList3 = combine_single_pass(entryList2)

    # Convert the list back to a dictionary then return it
    return dict(enumerate(entryList3, start=1))

#----------------------------------------------------------------------

# Calculate the number of characters per second for each subtitle entry
def calc_dict_speaking_rates(inputDict, dictKey='translated_text'):  
    tempDict = copy.deepcopy(inputDict)
    for key, value in tempDict.items():
        tempDict[key]['char_rate'] = round(len(value[dictKey]) / (int(value['duration_ms']) / 1000), 2)
    return tempDict

def calc_list_speaking_rates(inputList, charRateGoal, dictKey='translated_text'): 
    tempList = copy.deepcopy(inputList)
    for i in range(len(tempList)):
        # Calculate the number of characters per second based on the duration of the entry
        tempList[i]['char_rate'] = round(len(tempList[i][dictKey]) / (int(tempList[i]['duration_ms']) / 1000), 2)
        # Calculate the difference between the current char_rate and the goal char_rate - Absolute Value
        tempList[i]['char_rate_diff'] = abs(round(tempList[i]['char_rate'] - charRateGoal, 2))
    return tempList