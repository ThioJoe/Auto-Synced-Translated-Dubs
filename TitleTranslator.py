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

#===============================================================================================================

import auth
from utils import parseBool
TTS_API, TRANSLATE_API = auth.first_authentication()

outputFolder = "output"

import langcodes
import sys
import os
import configparser
import textwrap
import re

description = textwrap.dedent(description).strip("\n")

# Parse the description for hyperlinks and put the tags <span class="notranslate"></span> around them
# This prevents Google Translate from translating the links
description = re.sub(r'(https?://[^\s]+)', r' <span class="notranslate">\1</span> ', description)

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

batchSettings = {}
for num in languageNums:
    batchSettings[num] = {
        'synth_language_code': batchConfig[f'LANGUAGE-{num}']['synth_language_code'],
        'synth_voice_name': batchConfig[f'LANGUAGE-{num}']['synth_voice_name'],
        'translation_target_language': batchConfig[f'LANGUAGE-{num}']['translation_target_language'],
        'synth_voice_gender': batchConfig[f'LANGUAGE-{num}']['synth_voice_gender']
    }

#--------------------------------- Translate ---------------------------------
def translate(originalLanguage, targetLanguage, translationList):
    response = auth.TRANSLATE_API.projects().translateText(
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

    # Remove the span tags from the translated text, and convert the html formatting for special symbols
    for i, line in enumerate(translatedTexts):
        translatedTexts[i] = line.replace('<span class="notranslate">', '').replace('</span>', '')
        translatedTexts[i] = line.replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&#39;', '\'')

    return translatedTexts # Returns a list of translated texts
#--------------------------------------------------------------------------------


for key, value in batchSettings.items():
    result = translate(originalLanguage, value['translation_target_language'], translationList)
    # Pop out the first element of the list, which is the translated title, leave the rest (Description lines)
    batchSettings[key]['translated_title'] = result.pop(0)
    batchSettings[key]['translated_description'] = result

# Write the translated text to a file
with open(outputFolder + '/Translated Titles and Descriptions.txt', 'w', encoding='utf-8') as f:
    for key, value in batchSettings.items():
        title_translated = value['translated_title']
        description_translated = value['translated_description']
        lang = value['translation_target_language']
        langDisplay = langcodes.get(lang).display_name()
        
        # Re-add the empty lines to the description
        for i in emptyLineIndexes:
            description_translated.insert(i, '')

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
