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
noTranslateList = ['•', '⇨', '▼', '▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬']
originalLanguage = 'en'

# You can export a json file to use with the TitleDescriptionUpdater.py script to update the translated titles and descriptions automatically
createJsonFile = True

#===============================================================================================================
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

import Scripts.auth as auth
from Scripts.utils import parseBool
import Scripts.utils as utils
from Scripts.shared_imports import *
GOOGLE_TTS_API, GOOGLE_TRANSLATE_API = auth.first_authentication()

#outputFolder = "Outputs"

import langcodes
import configparser
import textwrap
import re
import html
import copy
import json

# --------------------------- SSML Customization Functions ---------------------------
from Scripts.translate import add_notranslate_tags_from_notranslate_file, remove_notranslate_tags, add_notranslate_tags_for_manual_translations, replace_manual_translations, process_response_text
# Import files and put into dictionaries
noTranslateOverrideFile = os.path.join('SSML_Customization', 'dont_translate_phrases.txt')
dontTranslateList = utils.txt_to_list(noTranslateOverrideFile)
manualTranslationOverrideFile = os.path.join('SSML_Customization', 'Manual_Translations.csv')
manualTranslationsDict = utils.csv_to_dict(manualTranslationOverrideFile)
urlListFile = os.path.join('SSML_Customization', 'url_list.txt')
urlList = utils.txt_to_list(urlListFile)
#--------------------------------------------------------------------------------------

description = textwrap.dedent(description).strip("\n")

# Parse the description for hyperlinks and put the tags <span class="notranslate"></span> around them
# This prevents Google Translate from translating the links
description = re.sub(r'(https?://[^\s]+)', r'<span class="notranslate">\1</span>', description, flags=re.IGNORECASE)

# Use span class="notranslate" to prevent translating certain characters
for item in noTranslateList:
    description = re.sub(r'(' + item + r'+)', r'<span class="notranslate">\1</span>', description)

# Use span class to prevent translating timestamp numbers, only matching if there is a newline or space before and after the timestamp
description = re.sub(r'(\n|\s)(\d+:\d+)(\n|\s)', r'\1<span class="notranslate">\2</span>\3', description)

# Add notranslate tags from SSML Customization files
description = add_notranslate_tags_from_notranslate_file(description, dontTranslateList)
description = add_notranslate_tags_from_notranslate_file(description, urlList)

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
languageNums = batchConfig['SETTINGS']['enabled_languages'].replace(' ','').split(',')

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
formalityPreference = config['formality_preference']
def set_translation_info(languageBatchDict):
    newBatchSettingsDict = copy.deepcopy(languageBatchDict)

    # Set the translation service for each language
    if cloudConfig['translate_service'] == 'deepl':
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
    elif cloudConfig['translate_service'] == 'google':
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

    # Add notranslate tags for manual translation (This must be done here because it is language dependent)
    # Run add_notranslate_tags_for_manual_translations on each line in the translationList, then re-join the list
    for i, line in enumerate(translationList):
        translationList[i] = add_notranslate_tags_for_manual_translations(line, targetLanguage)

    if translateService == 'google':
        response = auth.GOOGLE_TRANSLATE_API.projects().translateText(
            parent='projects/' + cloudConfig['google_project_id'],
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
        response = auth.DEEPL_API.translate_text(translationList, target_lang=targetLanguage, formality=formality, tag_handling='html')
        translatedTexts = [response[i].text for i in range(len(response))]

    # Remove the span tags from the translated text, unescape HTML symbols, replace manual translations
    for i, line in enumerate(translatedTexts):
        newText = process_response_text(line, targetLanguage)
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
with open(os.path.join(OUTPUT_FOLDER , 'Translated Titles and Descriptions.txt'), 'w', encoding='utf-8') as f:
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
    with open(os.path.join(OUTPUT_FOLDER , 'Translated Items.json'), 'w', encoding='utf-8') as f:
        json.dump(batchSettings, f, indent=4)

