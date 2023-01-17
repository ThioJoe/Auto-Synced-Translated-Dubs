#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#--------------------------------------------------
# Title and Description Translator
# Standalone script that makes it easy to translates the title and description of a YouTube video to multiple languages


# SET THE TITLE AND DESCRIPTION TEXT, AND VARIABLES IN THIS SECTION
# Note: Make sure to keep the triple quotes around the text, don't remove the "r" before them
#===============================================================================================================
title = r"""Title of the video here"""

description = r"""
You can put the description here
Just paste it as is, in the lines between the triple quotes

It will be translated to all the languages you have enabled in the batch config file
It will put all the results in a text file in a way that you can easily copy and paste each one
The file wil be called 'Translated Titles and Descriptions.txt' and go in the output folder

It will avoid translating timestamps, links, and any characters you specify in the noTranslateList variable
It will also preserve newlines, so you can use them to separate paragraphs
"""

# Characters to avoid translating. Update this with any characters that you don't want translated
noTranslateList = ['•', '⇨', '▼', '😤', '▬']
originalLanguage = 'en'

# You can export a json file to use with the TitleDescriptionUpdater.py script to update the translated titles and descriptions automatically
createJsonFile = False

#===============================================================================================================

import auth
from utils import parseBool
GOOGLE_TTS_API, GOOGLE_TRANSLATE_API = auth.first_authentication()

outputFolder = "Outputs"

import langcodes
import sys
import os
import configparser
import textwrap
import re
import html
import copy
import json

description = textwrap.dedent(description).strip("\n")

# Parse the description for hyperlinks and put the tags <span class="notranslate"></span> around them
# This prevents Google Translate from translating the links
description = re.sub(r'(https?://[^\s]+)', r' <span class="notranslate">\1</span> ', description, flags=re.IGNORECASE)

# Use span class="notranslate" to prevent translating certain characters
for char in noTranslateList:
    description = re.sub(r'(' + char + r'+)', r' <span class="notranslate">\1</span> ', description)

# Use span class to prevent translating timestamp numbers, only matching if there is a newline or space before and after the timestamp
description = re.sub(r'(\n|\s)(\d+:\d+)(\n|\s)', r'\1<span class="notranslate">\2</span>\3', description)


# Split the description into a list of lines, so newlines can be preserved and re-applied after translation
description = description.splitlines()

# Create list of lines with empty lines, then remove the empty lines to prepare for translation
emptyLineIndexes = []
for i, text in enumerate(description):
    if text.strip() == '':
        emptyLineIndexes.append(i)
for line in description:
    if line.strip() == '':
        description.remove(line)


# List with title as first element and description lines as the rest
translationList = [title] + description

# Get data from batch config file
batchConfig = configparser.ConfigParser()
batchConfig.read('batch.ini')
languageNums = batchConfig['SETTINGS']['enabled_languages'].replace(' ','').split(',')
cloudConfig = configparser.ConfigParser()
cloudConfig.read('cloud_service_settings.ini')
googleProjectID = cloudConfig['CLOUD']['google_project_id']
preferredTranslateService = cloudConfig['CLOUD']['translate_service']
config = configparser.ConfigParser()
config.read('config.ini')

batchSettings = {}
for num in languageNums:
    batchSettings[num] = {
        'synth_language_code': batchConfig[f'LANGUAGE-{num}']['synth_language_code'],
        'synth_voice_name': batchConfig[f'LANGUAGE-{num}']['synth_voice_name'],
        'translation_target_language': batchConfig[f'LANGUAGE-{num}']['translation_target_language'],
        'synth_voice_gender': batchConfig[f'LANGUAGE-{num}']['synth_voice_gender']
    }

##### Add additional info to the dictionary for each language #####
# Later put this function somewhere else
formalityPreference = config['SETTINGS']['formality_preference']
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

batchSettings = set_translation_info(batchSettings) # Use same function from main.py

#--------------------------------- Translate ---------------------------------
def translate(originalLanguage, singleLangDict, translationList):
    targetLanguage = singleLangDict['translation_target_language']
    translateService = singleLangDict['translate_service']
    formality = singleLangDict['formality']

    print(" Translating to " + targetLanguage + " using " + translateService + "...                    ", end='\r')

    if translateService == 'google':
        response = auth.GOOGLE_TRANSLATE_API.projects().translateText(
            parent='projects/' + googleProjectID,
            body={
                'contents':translationList,
                'sourceLanguageCode': originalLanguage,
                'targetLanguageCode': targetLanguage,
                'mimeType': 'text/html',
                #'model': 'nmt',
                #'glossaryConfig': {}
            }
        ).execute()
        translatedTexts = [response['translations'][i]['translatedText'] for i in range(len(response['translations']))]
    elif translateService == 'deepl':
        response = auth.DEEPL_API.translate_text(translationList, target_lang=targetLanguage, formality=formality)
        translatedTexts = [response[i].text for i in range(len(response))]

    # Remove the span tags from the translated text, and convert the html formatting for special symbols
    for i, line in enumerate(translatedTexts):
        newText = line.replace('<span class="notranslate">', '').replace('</span>', '')
        newText = html.unescape(newText)
        translatedTexts[i] = newText

    return translatedTexts # Returns a list of translated texts
#--------------------------------------------------------------------------------


for langNum, langData in batchSettings.items():
    result = translate(originalLanguage, langData, translationList)
    # Pop out the first element of the list, which is the translated title, leave the rest (Description lines)
    batchSettings[langNum]['translated_title'] = result.pop(0)
    batchSettings[langNum]['translated_description'] = result

# Reinsert the empty lines into the description
for i in emptyLineIndexes:
    for langNum, langData in batchSettings.items():
        langData['translated_description'].insert(i, '')

# Write the translated text to a file
with open(os.path.join(outputFolder , 'Translated Titles and Descriptions.txt'), 'w', encoding='utf-8') as f:
    for langNum, langData in batchSettings.items():
        title_translated = langData['translated_title']
        description_translated = langData['translated_description']
        lang = langData['translation_target_language']
        langDisplay = langcodes.get(lang).display_name()

        # Write heading for each language
        f.write(f'==============================================================================\n')
        f.write(f'=================================== {langDisplay} ===================================\n')
        f.write(f'==============================================================================\n\n')
        f.write(f'{title_translated}\n')
        f.write("--------------------------------------------------------------------------------\n\n\n")
        # Write the translated description
        for line in description_translated:
            f.write(f'{line}\n')
      
        f.write("\n\n\n")

if createJsonFile:
    # Convert each description to single line
    for langNum, langData in batchSettings.items():
        langData['translated_description'] = '\n'.join(langData['translated_description'])

    # Write the translated items to a json file
    with open(os.path.join(outputFolder , 'Translated Items.json'), 'w', encoding='utf-8') as f:
        json.dump(batchSettings, f, indent=4)

