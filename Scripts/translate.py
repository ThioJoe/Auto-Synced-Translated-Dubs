#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Imports
from Scripts.shared_imports import *
import Scripts.auth as auth
import Scripts.utils as utils

import configparser
from operator import itemgetter
import sys
import copy
import os
import pathlib
import langcodes
import html

# -------------------------------- No Translate and Manual Translation Functions -----------------------------------

# Import files and put into dictionaries
noTranslateOverrideFile = os.path.join('SSML_Customization', 'dont_translate_phrases.txt')
dontTranslateList = utils.txt_to_list(noTranslateOverrideFile)
manualTranslationOverrideFile = os.path.join('SSML_Customization', 'Manual_Translations.csv')
manualTranslationsDict = utils.csv_to_dict(manualTranslationOverrideFile)
urlListFile = os.path.join('SSML_Customization', 'url_list.txt')
urlList = utils.txt_to_list(urlListFile)

# Add span tags around certain words to exclude them from being translated
def add_notranslate_tags_from_notranslate_file(text, phraseList, customNoTranslateTag=None):
    for word in phraseList:
        findWordRegex = rf'\b{word}\b'
        findWordRegexCompiled = regex.compile(findWordRegex, flags=re.IGNORECASE | re.UNICODE)

        if not customNoTranslateTag:
            # Directly replace the word with a span tag
            text = findWordRegexCompiled.sub(rf'<span class="notranslate">{word}</span>', text)
        else:
            # Replace the word with a custom XML tag
            text = findWordRegexCompiled.sub(rf'<{customNoTranslateTag}>{word}</{customNoTranslateTag}>', text)
    return text

def remove_notranslate_tags(text, customNoTranslateTag=None):
    if customNoTranslateTag == None:
        text = text.replace('<span class="notranslate">', '').replace('</span>', '')
    else:
        text = text.replace(f'<{customNoTranslateTag}>', '').replace(f'</{customNoTranslateTag}>', '')
    return text

def add_notranslate_tags_for_manual_translations(text, langcode, customTag=None):
    for manualTranslatedText in manualTranslationsDict:
        # Only replace text if the language matches the entry in the manual translations file
        if manualTranslatedText['Language Code'] == langcode: 
            originalText = manualTranslatedText['Original Text']
            findWordRegex = rf'\b{originalText}\b'
            findWordRegexCompiled = regex.compile(findWordRegex, flags=re.IGNORECASE | re.UNICODE)

            if customTag is None:
                replacement = rf'<span class="notranslate">{originalText}</span>'
            else:
                replacement = rf'<{customTag}>{originalText}</{customTag}>'

            text = findWordRegexCompiled.sub(replacement, text)

    return text

# Replace certain words or phrases with their manual translation
def replace_manual_translations(text, langcode):
    for manualTranslatedText in manualTranslationsDict:
        # Only replace text if the language matches the entry in the manual translations file
        if manualTranslatedText['Language Code'] == langcode: 
            originalText = manualTranslatedText['Original Text']
            translatedText = manualTranslatedText['Translated Text']
            findWordRegex = rf'\b{originalText}\b'
            findWordRegexCompiled = regex.compile(findWordRegex, flags=re.IGNORECASE | re.UNICODE)
            # Substitute the matched word with the translated text
            text = findWordRegexCompiled.sub(translatedText, text)

    return text


def ends_with_sentence_terminator(text):
    # List of sentence terminators in different languages
    sentence_terminators = [
        '.', '. ', '!', '! ', '?', '? ', '."', '." ',  # English and similar
        '。',  # Japanese, Chinese
        '…',  # Ellipsis
        '¿', '¡',  # Spanish inverted punctuation
        '۔',  # Arabic full stop
        '।',  # Devanagari (Hindi, etc.)
        '๏',  # Thai full stop
        # Add additional language-specific terminators as needed
    ]
    # Returns boolean
    return any(text.endswith(terminator) for terminator in sentence_terminators)


#======================================== Translate Text ================================================
# Note: This function was almost entirely written by GPT-3 after feeding it my original code and asking it to change it so it
# would break up the text into chunks if it was too long. It appears to work

def process_response_text(text, targetLanguage, customNoTranslateTag=None):
    text = html.unescape(text)
    text = remove_notranslate_tags(text, customNoTranslateTag)
    text = replace_manual_translations(text, targetLanguage)
    return text

def split_transcript_chunks(text, max_length=5000):
    # Calculate the total number of utf-8 codepoints
    #totalCodepoints = len(text.encode("utf-8"))
    
    # Split the transcript into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Initialize a list to store the chunks of text
    chunks = []
    
    # Initialize a string to store a chunk of text
    chunk = ""
    
    # For each sentence in the list of sentences
    for sentence in sentences:
        # If adding the sentence to the chunk would keep it within the maximum length
        if len(chunk.encode("utf-8")) + len(sentence.encode("utf-8")) + 1 <= max_length:  # Adding 1 to account for space
            # Add the sentence to the chunk
            chunk += sentence + " "
        else:
            # If adding the sentence would exceed the maximum length and chunk is not empty
            if chunk:
                # Add the chunk to the list of chunks
                chunks.append(chunk.strip())
            # Start a new chunk with the current sentence
            chunk = sentence + " "
    
    # Add the last chunk to the list of chunks (if it's not empty)
    if chunk:
        chunks.append(chunk.strip())
    
    # Return the list of chunks
    return chunks

def convertChunkListToCompatibleDict(chunkList):
    # Create dictionary with numbers as keys and chunks as values
    chunkDict = {}
    for i, chunk in enumerate(chunkList, 1):
        chunkDict[str(i)] = {'text': chunk}
    return chunkDict

# Add marker custom marker tags
def add_marker_and_convert_to_string(textList, customMarkerTag):
    # If no brackets already on custom marker tag, add them
    if customMarkerTag[0] != '<':
        customMarkerTag = '<' + customMarkerTag
    if customMarkerTag[-1] != '>':
        customMarkerTag = customMarkerTag + '>'
    
    combinedString  = ""
    for i, text in enumerate(textList):
        # If last line don't add the tag
        if i == len(textList) - 1:
            combinedString += text
        else:
            combinedString += text + f" {customMarkerTag}"
    return combinedString

def split_and_clean_marked_combined_string(originalCombinedString, customMarkerTag, removeExtraAddedTag=None):
    # Fix issue where sometimes double commas or punctuation are added near tags
    punctuation = ",、.。"  # Add more comma types if needed
    escapedPunctuationChars = re.escape(punctuation)
    doublePunctuationPattern = rf"([.{escapedPunctuationChars}]\s*(?:<[^>]+>\s*)*[.{escapedPunctuationChars}]?\s*{customMarkerTag}\s*)[.{escapedPunctuationChars}]"
    # Replace the entire match with the captured group (excluding the redundant period)
    fixedCombinedString = re.sub(doublePunctuationPattern, r'\1', originalCombinedString)
    
    # Fix issue where a comma is placed after the marker tag, which causes comma to be at the beginning of a line
    fixMisplacedCommaPattern = rf"({customMarkerTag}\s?)([{escapedPunctuationChars}])"
    fixedCombinedString = re.sub(fixMisplacedCommaPattern, r"\2\1", fixedCombinedString)
    
    # Fix issue where after a custom  marker tag, an extra space is added between the next punctuation. This matches any ending html tag, then a space, then a punctuation character
    fixExtraSpaceAfterTagPattern = rf"(</[^>]+>)\s+([{escapedPunctuationChars}])"
    fixedCombinedString = re.sub(fixExtraSpaceAfterTagPattern, r"\1\2", fixedCombinedString)
    
    # # Fix resulting comma appearing directly after period after correcting other issues
    # escaped_periods = re.escape(".。")  # Standard and Japanese periods
    # escaped_commas = re.escape(",、")  # Standard and Japanese commas
    # commaAfterPeriodPattern = rf"([{escaped_periods}])([{escaped_commas}])"
    # # Use re.sub to remove the comma in such cases (replace with just the period)
    # fixedCombinedString = re.sub(commaAfterPeriodPattern, r"\1", fixedCombinedString)
    
    # Fix issue where hyphen is placed in addition to comma resulting in -,
    fixedCombinedString = fixedCombinedString.replace(f' -,', f',')

    # Split the translated text into chunks based on the custom marker tags, and remove the tags
    textList = fixedCombinedString.split(f'{customMarkerTag}')
    # Strip spaces off ends of lines, then remove tag, and strip spaces again to remove any leftover
    textList = [text.strip() for text in textList]
    textList = [text.replace(f'{customMarkerTag}', '') for text in textList]
    textList = [text.strip() for text in textList]
    
    # Remove extra added tags by Google translate or other service
    if removeExtraAddedTag:
        textList = [text.replace(removeExtraAddedTag, '') for text in textList]
        
    # Handle blank lines. DeepL seems to do this and sometimes combines the line after the blank line
    # This will find the index of a blank line, then split the following line into approximately 2 equal parts, ensuring not to split a word by splitting at the next space near the middle
    # It will put the first half into the blank line, and the second half into the next line
    for i, text in enumerate(textList):
        if text == '':
            nextLineIndex = i + 1
            while textList[nextLineIndex] == '':
                nextLineIndex += 1
            # Find the middle index
            middle = len(textList[nextLineIndex]) // 2
            # Adjust middle index to avoid splitting a word
            while middle < len(textList[nextLineIndex]) and textList[nextLineIndex][middle] not in [' ', '\n']:
                middle += 1
            # Split the next line at the adjusted middle index
            textList[i] = textList[nextLineIndex][:middle].rstrip()
            textList[nextLineIndex] = textList[nextLineIndex][middle:].lstrip()

            # In future may need to split line with text into however many blank lines there are plus 1 for itself
               
    
    return textList

def translate_with_google_and_process(textList, targetLanguage):
    # Set an html tag that will be used as marker to split the text later. Must be treated as neutral by Google Cloud, which seems to only be found by trial and error
    customMarkerTag = '<b>'
    endingTag = '</b>'
    
    combinedChunkTextString = add_marker_and_convert_to_string(textList, customMarkerTag=customMarkerTag)
    
    response = auth.GOOGLE_TRANSLATE_API.projects().translateText(
        parent='projects/' + cloudConfig['google_project_id'],
        body={
            'contents': combinedChunkTextString,
            'sourceLanguageCode': config['original_language'],
            'targetLanguageCode': targetLanguage,
            'mimeType': 'text/html',
            #'model': 'nmt',
            #'glossaryConfig': {}
        }
    ).execute()
    translatedTextString = response['translations'][0]['translatedText']
    
    # Clean and process text
    translatedTextsList = split_and_clean_marked_combined_string(translatedTextString, customMarkerTag=customMarkerTag, removeExtraAddedTag=endingTag)
    translatedTextsList = [process_response_text(translatedTextsList[i], targetLanguage) for i in range(len(translatedTextsList))]
    return translatedTextsList

def translate_with_deepl_and_process(textList, targetLanguage, formality=None, customNoTranslateTag='zzz'):
    # Create combined string of all the text in the textList, but add custom marker tags <zzz> to the end to note where the original text was split. But don't add to last line.
    # In future can possibly add information such as index to tag, such as <zzz=#>.
    combinedChunkTextString = add_marker_and_convert_to_string(textList, customMarkerTag='<xxx>')
            
    # Put string into list by itself, as apparently required by DeepL API
    textListToSend = [combinedChunkTextString]
    
    # Send the Request, then extract translated text as string from the response
    result = auth.DEEPL_API.translate_text(textListToSend, target_lang=targetLanguage, formality=formality, tag_handling='xml', ignore_tags=[customNoTranslateTag, 'xxx'])
    translatedText = result[0].text
    
    # Handle weird quirk of DeepL where it adds parenthesis around the tag sometimes
    # Pattern to find parentheses around the custom tag with potential spaces. Also handles full width parenthesis
    pattern = r'[（(]\s*<xxx>\s*[）)]'
    translatedText = re.sub(pattern, ' <xxx>', translatedText)
    
    # Split the translated text into chunks based on the custom marker tags, and remove the tags
    translatedTextsList = split_and_clean_marked_combined_string(translatedText, customMarkerTag='<xxx>')
   
    # Extract the translated texts from the response and process them
    translatedProcessedTextsList = [process_response_text(translatedTextsList[i], targetLanguage, customNoTranslateTag=customNoTranslateTag) for i in range(len(translatedTextsList))]
    return translatedProcessedTextsList

# Translate the text entries of the dictionary
def translate_dictionary(inputSubsDict, langDict, skipTranslation=False, transcriptMode=False, forceNativeSRTOutput=False):
    targetLanguage = langDict['targetLanguage']
    translateService = langDict['translateService']
    formality = langDict['formality']

    # Create a container for all the text to be translated
    textToTranslate = []
    
    # Set Custom Tag if supported by the translation service
    if translateService == 'deepl':
        customNoTranslateTag = 'zzz'
    else:
        customNoTranslateTag = None

    for key in inputSubsDict:
        originalText = inputSubsDict[key]['text']
        # Add any 'notranslate' tags to the text
        processedText = add_notranslate_tags_from_notranslate_file(originalText, dontTranslateList, customNoTranslateTag)
        processedText = add_notranslate_tags_from_notranslate_file(processedText, urlList, customNoTranslateTag)
        processedText = add_notranslate_tags_for_manual_translations(processedText, targetLanguage, customNoTranslateTag)

        # Add the text to the list of text to be translated
        textToTranslate.append(processedText)
   
    #Calculate the total number of utf-8 codepoints - No longer needed, but keeping just in case
    # codepoints = 0
    # for text in textToTranslate:
    #     codepoints += len(text.encode("utf-8"))
      
    if skipTranslation == False:
        maxLines = None
        # Set maxCodePoints based on translate service. This will determine the chunk size
        # Google's API limit is 30000 Utf-8 codepoints per request, while DeepL's is 130000, but we leave some room just in case
        if translateService == 'google':
            # maxCodePoints = 27000
            maxCodePoints = 5000 # Not the hard limit, but recommended
            # For the workaround to get it to keep HTML markers in place, can't do more than 50 subtitle lines worth, so set 40 for buffer
            # This isn't a limit for the request, but how many lines can be combined into a single string for the workaround
            maxLines = 40
        elif translateService == 'deepl':
            maxCodePoints = 100000
            maxLines = 999999 # No such needed limit for DeepL, but set to a high number just in case
            
        # Create a list of lists - 'chunkedTexts' where each list is a 'chunk', which in itself contains a list of strings of text to be translated
        chunkedTexts = []
        currentChunk = []
        currentCodePoints = 0

        for text in textToTranslate:
            textCodePoints = len(text.encode("utf-8")) + 7 # Add 7 to account for custom tag to be added later
            
            if currentChunk and translateService == 'deepl':
                # Check if adding the current text will exceed the limit and if it ends with a period or period followed by a space
                if (currentCodePoints + textCodePoints > maxCodePoints) and text.endswith(('.', '. ','!','! ','?','? ', '."','." ')):
                    chunkedTexts.append(currentChunk)
                    currentChunk = []
                    currentCodePoints = 0
                    
            # For google need to additionally check for maxLines
            elif currentChunk and translateService == 'google':
                # Set soft limit of 40 lines or 5000 code points, where only splits chunk if ending sentence
                if (len(currentChunk) >= maxLines or currentCodePoints + textCodePoints > maxCodePoints) and text.endswith(('.', '. ','!','! ','?','? ', '."','." ')):
                    chunkedTexts.append(currentChunk)
                    currentChunk = []
                    currentCodePoints = 0
                # Set hard limit of 50 lines or 27000 code points, where it will split chunk even if not ending sentence
                elif (len(currentChunk) >= 50 or currentCodePoints + textCodePoints > 27000):
                    chunkedTexts.append(currentChunk)
                    currentChunk = []
                    currentCodePoints = 0
                

            currentChunk.append(text)
            currentCodePoints += textCodePoints

        # Add the last chunk if it's not empty
        if currentChunk:
            chunkedTexts.append(currentChunk)
        
        # # Create a list of lists - 'chunkedTexts' where each list is a 'chunk', which in itself contains a list of strings of text to be translated
        # for text in textToTranslate:
        #     textCodePoints = len(text.encode("utf-8")) + 7 # Add 7 to account for custom tag to be added later
            
        #     # Check if adding the current text will exceed the limit or if it ends with a period
        #     if (currentCodePoints + textCodePoints > maxCodePoints and currentChunk) and text.endswith(('.', '. ')):
        #         chunkedTexts.append(currentChunk)
        #         currentChunk = []
        #         currentCodePoints = 0

        #     currentChunk.append(text)
        #     currentCodePoints += textCodePoints
        # ---------------------------------------------
        
        subIndexToAddTo = 1 # Need to start at 1 because the dictionary keys start at 1, not 0
        # Handle each chunk in sequence, instead of all (chunkedTexts) at once
        for j,chunk in enumerate(chunkedTexts):
                      
            # Send the request
            if translateService == 'google':
                serviceName = "Google"
                print(f'[Google] Translating text group {j+1} of {len(chunkedTexts)}')
                translatedTexts = translate_with_google_and_process(chunk, targetLanguage)

            elif translateService == 'deepl':
                serviceName = "DeepL"
                print(f'[DeepL] Translating text group {j+1} of {len(chunkedTexts)}')
                translatedTexts = translate_with_deepl_and_process(chunk, targetLanguage, formality=formality, customNoTranslateTag=customNoTranslateTag)
                
            else:
                print("Error: Invalid translate_service setting. Only 'google' and 'deepl' are supported.")
                sys.exit()
                
            # Add the translated texts to the dictionary
            for i in range(len(chunkedTexts[j])):
                key = str(subIndexToAddTo) 
                inputSubsDict[key]['translated_text'] = translatedTexts[i]
                subIndexToAddTo += 1
                # Print progress, ovwerwrite the same line
                print(f' Translated with {serviceName}: {key} of {len(inputSubsDict)}', end='\r')

    else:
        for key in inputSubsDict:
            inputSubsDict[key]['translated_text'] = process_response_text(inputSubsDict[key]['text'], targetLanguage) # Skips translating, such as for testing
    print("                                                  ")
    
    # If translating transcript, return the translated text
    if transcriptMode:
        return inputSubsDict

    # # Debug export inputSubsDict as json for offline testing
    # import json
    # with open('inputSubsDict.json', 'w') as f:
    #     json.dump(inputSubsDict, f)

    # # DEBUG import inputSubsDict from json for offline testing
    # import json
    # with open('inputSubsDict.json', 'r') as f:
    #     inputSubsDict = json.load(f)

    combinedProcessedDict = combine_subtitles_advanced(inputSubsDict, int(config['combine_subtitles_max_chars']))

    if skipTranslation == False or config['debug_mode'] == True or forceNativeSRTOutput == True:
        # Use video file name to use in the name of the translate srt file, also display regular language name
        lang = langcodes.get(targetLanguage).display_name()

        if forceNativeSRTOutput:
            translatedSrtFileName = pathlib.Path(ORIGINAL_VIDEO_PATH).stem + f"- Original_Combined - {lang} - {targetLanguage}.srt"
        else:
            translatedSrtFileName = pathlib.Path(ORIGINAL_VIDEO_PATH).stem + f" - {lang} - {targetLanguage}.srt"
        # Set path to save translated srt file
        translatedSrtFileName = os.path.join(OUTPUT_FOLDER, translatedSrtFileName)
        
        # Write new srt file with translated text
        with open(translatedSrtFileName, 'w', encoding='utf-8-sig') as f:
            for key in combinedProcessedDict:
                f.write(str(key) + '\n')
                f.write(combinedProcessedDict[key]['srt_timestamps_line'] + '\n')
                f.write(combinedProcessedDict[key]['translated_text'] + '\n')
                f.write('\n')
        
        # Write debug version if applicable
        if config['debug_mode']:
            if os.path.isfile(ORIGINAL_VIDEO_PATH):
                DebugSrtFileName = pathlib.Path(ORIGINAL_VIDEO_PATH).stem + f" - {lang} - {targetLanguage}.DEBUG.txt"
            else:
                DebugSrtFileName = "debug" + f" - {lang} - {targetLanguage}.DEBUG.txt"
                
            DebugSrtFileName = os.path.join(OUTPUT_FOLDER, DebugSrtFileName)
            
            with open(DebugSrtFileName, 'w', encoding='utf-8-sig') as f:
                for key in combinedProcessedDict:
                    f.write(str(key) + '\n')
                    f.write(combinedProcessedDict[key]['srt_timestamps_line'] + '\n')
                    f.write(combinedProcessedDict[key]['translated_text'] + '\n')
                    f.write(f"DEBUG: duration_ms = {combinedProcessedDict[key]['duration_ms']}" + '\n')
                    f.write(f"DEBUG: char_rate = {combinedProcessedDict[key]['char_rate']}" + '\n')
                    f.write(f"DEBUG: start_ms = {combinedProcessedDict[key]['start_ms']}" + '\n')
                    f.write(f"DEBUG: end_ms = {combinedProcessedDict[key]['end_ms']}" + '\n')
                    f.write(f"DEBUG: start_ms_buffered = {combinedProcessedDict[key]['start_ms_buffered']}" + '\n')
                    f.write(f"DEBUG: end_ms_buffered = {combinedProcessedDict[key]['end_ms_buffered']}" + '\n')
                    f.write(f"DEBUG: Number of chars = {len(combinedProcessedDict[key]['translated_text'])}" + '\n')
                    f.write('\n')

    # FOR TESTING - Put all translated text into single string
    # translatedText = ""
    # for key in combinedProcessedDict:
    #     translatedText += combinedProcessedDict[key]['translated_text']
    
    return combinedProcessedDict

def download_youtube_auto_translations(languageCodeList, videoID):
    
    def get_captions_list(videoID):
        results = auth.YOUTUBE_API.captions().list(
            part="snippet",
            videoId=videoID
        ).execute()
        return results
    captionsTracksResponse = get_captions_list(videoID)
    
    # Find the caption ID for a specific language
    def get_caption_id(captionsTracksResponse, desiredLanguageCode):
        def check_code(code):
            matchedID = None
            for item in captionsTracksResponse["items"]:
                if item["snippet"]["language"] == code:
                    matchedID = item["id"]
                    break
            return matchedID
                
        captionID = check_code(desiredLanguageCode)
        
        # If none found, check for two-letter code (first two letters)
        if captionID == None:
            captionID = check_code(desiredLanguageCode[:2])
            
        return captionID
      
    def download_yt_translated_captions_track(captionID, desiredLanguageCode=None, tfmt='srt'):
        results = auth.YOUTUBE_API.captions().download(
            id=captionID,
            tlang=desiredLanguageCode,
            tfmt=tfmt
        ).execute()
        
        if type(results) is not bytes:
            print("\nError: YouTube API call failed to return subtitles.")
            return False
        
        # Make output folder if it doesn't exist
        if not os.path.exists(OUTPUT_FOLDER):
            os.makedirs(OUTPUT_FOLDER)
        
        # Save captions to file. API call returns bytes in specified format
        with open(os.path.join(OUTPUT_FOLDER, f'{ORIGINAL_VIDEO_NAME} - {desiredLanguageCode}.srt'), 'wb') as f:
            # Write the captions bytes to file
            f.write(results)
            
        return True
    
    # Get native language caption ID
    nativeCaptionID = get_caption_id(captionsTracksResponse, config['original_language'])
    
    # Download the captions for each language
    for langCode in languageCodeList:
        langCaptionID = get_caption_id(captionsTracksResponse, langCode)
        
        # If no matched language track, use native caption ID then auto-translate
        if langCaptionID == None:
            langCaptionID = nativeCaptionID
        
        download_yt_translated_captions_track(langCaptionID, langCode)
    

##### Add additional info to the dictionary for each language #####
def set_translation_info(languageBatchDict):
    newBatchSettingsDict = copy.deepcopy(languageBatchDict)

    if config['skip_translation'] == True:
        for langNum, langInfo in languageBatchDict.items():
            newBatchSettingsDict[langNum]['translate_service'] = None
            newBatchSettingsDict[langNum]['formality'] = None
        return newBatchSettingsDict
        
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
                if config['formality_preference'] == 'more':
                    newBatchSettingsDict[langNum]['formality'] = 'prefer_more'
                elif config['formality_preference'] == 'less':
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

    else:
        print("Error: No valid translation service selected. Please choose a valid service or enable 'skip_translation' in config.")
        sys.exit()

    return newBatchSettingsDict    


#======================================== Combine Subtitle Lines ================================================
def combine_subtitles_advanced(inputDict, maxCharacters=200):
    # Set gap threshold, the maximum gap between subtitles to combine
    if 'subtitle_gap_threshold_milliseconds' in config:
        gapThreshold = int(config['subtitle_gap_threshold_milliseconds'])
    else:
        gapThreshold = 200
    
    if ('speech_rate_goal' in config and config['speech_rate_goal'] == 'auto') or ('speech_rate_goal' not in config):
        # Calculate average char rate goal by dividing the total number of characters by the total duration in seconds from the last subtitle timetsamp
        totalCharacters = 0
        totalDuration = 0
        for key, value in inputDict.items():
            totalCharacters += len(value['translated_text'])
            totalDuration = int(value['end_ms']) / 1000 # Just ends up staying as last subtitle timestamp
        charRateGoal = totalCharacters / totalDuration
        charRateGoal = round(charRateGoal, 2)
    else:
        charRateGoal = config['speech_rate_goal']
    
    # Don't change this, it is not an option, it is for keeping track
    noMorePossibleCombines = False
    # Convert dictionary to list of dictionaries of the values
    entryList = []

    for key, value in inputDict.items():
        value['originalIndex'] = int(key)-1
        entryList.append(value)

    while not noMorePossibleCombines:
        entryList, noMorePossibleCombines = combine_single_pass(entryList, charRateGoal, gapThreshold, maxCharacters)

    # Convert the list back to a dictionary then return it
    return dict(enumerate(entryList, start=1))

def combine_single_pass(entryListLocal, charRateGoal, gapThreshold, maxCharacters):   
    ## Don't change these, they are not options, they are for keeping track ##
    # Want to restart the loop if a change is made, so use this variable, otherwise break only if the end is reached
    reachedEndOfList = False
    noMorePossibleCombines = True # Will be set to False if a combination is made

    # Use while loop because the list is being modified
    while not reachedEndOfList:

        # Need to update original index in here
        for entry in entryListLocal:
            entry['originalIndex'] = entryListLocal.index(entry)

        # Will use later to check if an entry is the last one in the list, because the last entry will have originalIndex equal to the length of the list - 1
        originalNumberOfEntries = len(entryListLocal)

        # Need to calculate the char_rate for each entry, any time something changes, so put it at the top of this loop
        entryListLocal = calc_list_speaking_rates(entryListLocal, charRateGoal)

        # Sort the list by the difference in speaking speed from charRateGoal, this will ensure the most extreme fast or slow segments are combined first
        priorityOrderedList = sorted(entryListLocal, key=itemgetter('char_rate_diff'), reverse=True) 

        # Iterates through the list in order of priority, and uses that index to operate on entryListLocal
        # For loop is broken after a combination is made, so that the list can be re-sorted and re-iterated
        for progress, data in enumerate(priorityOrderedList):
            i = data['originalIndex']
            # Check if last entry, and therefore will end loop when done with this iteration
            if progress == len(priorityOrderedList) - 1:
                reachedEndOfList = True

            # Check if the current entry is outside the upper and lower bounds
            if (data['char_rate'] > charRateGoal or data['char_rate'] < charRateGoal):

                # Check if the entry is the first in entryListLocal, if so do not consider the previous entry
                if data['originalIndex'] == 0:
                    considerPrev = False
                else:
                    considerPrev = True

                # Check if the entry is the last in entryListLocal, if so do not consider the next entry
                if data['originalIndex'] == originalNumberOfEntries - 1:
                    considerNext = False
                else:
                    considerNext = True
              
                # Get the char_rate of the next and previous entries, if they exist, and calculate the difference
                # If the diff is positive, then it is lower than the current char_rate
                try:
                    nextCharRate = entryListLocal[i+1]['char_rate']
                    nextDiff = data['char_rate'] - nextCharRate
                except IndexError:
                    considerNext = False
                    nextCharRate = None
                    nextDiff = None
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
                
            # If user has set option to increase maximum characters when speeds are extreme. Increase by various amounts depending on how extreme
            if 'increase_max_chars_for_extreme_speeds' in config and config['increase_max_chars_for_extreme_speeds'] == True:
                if data['char_rate'] > 28:
                    tempMaxChars = maxCharacters + 100
                elif data['char_rate'] > 27:
                    tempMaxChars = maxCharacters + 85
                elif data['char_rate'] > 26:
                    tempMaxChars = maxCharacters + 70
                elif data['char_rate'] > 25:
                    tempMaxChars = maxCharacters + 50
                else:
                    tempMaxChars = maxCharacters
            else:
                tempMaxChars = maxCharacters

            # Choose whether to consider next and previous entries, and if neither then continue to next loop
            if data['char_rate'] > charRateGoal:
                # Check to ensure next/previous rates are lower than current rate, and the combined entry is not too long, and the gap between entries is not too large
                # Need to add check for considerNext and considerPrev first, because if run other checks when there is no next/prev value to check, it will throw an error
                if considerNext == False or not nextDiff or nextDiff < 0 or (entryListLocal[i]['break_until_next'] >= gapThreshold) or (len(entryListLocal[i]['translated_text']) + len(entryListLocal[i+1]['translated_text']) > tempMaxChars):
                    considerNext = False
                try:
                    if considerPrev == False or not prevDiff or prevDiff < 0 or (entryListLocal[i-1]['break_until_next'] >= gapThreshold) or (len(entryListLocal[i-1]['translated_text']) + len(entryListLocal[i]['translated_text']) > tempMaxChars):
                        considerPrev = False
                except TypeError:
                    considerPrev = False

            elif data['char_rate'] < charRateGoal:
                # Check to ensure next/previous rates are higher than current rate
                if considerNext == False or not nextDiff or nextDiff > 0 or (entryListLocal[i]['break_until_next'] >= gapThreshold) or (len(entryListLocal[i]['translated_text']) + len(entryListLocal[i+1]['translated_text']) > tempMaxChars):
                    considerNext = False
                try:
                    if considerPrev == False or not prevDiff or prevDiff > 0 or (entryListLocal[i-1]['break_until_next'] >= gapThreshold) or (len(entryListLocal[i-1]['translated_text']) + len(entryListLocal[i]['translated_text']) > tempMaxChars):
                        considerPrev = False
                except TypeError:
                    considerPrev = False
            else:
                continue

            # Continue to next loop if neither are considered
            if not considerNext and not considerPrev:
                continue

            #### Should only reach this point if two entries are to be combined ####
            
            # If either direction of combining is possible, then prefer the one that will combine partial sentence fragments - !!!EXPERIMENTAL!!!
            # Also will prefer to not combine such that it adds a line after a sentence terminator
            if 'prioritize_avoiding_fragmented_speech' in config: # In case user didn't update config file
                preferSentenceEnd = config['prioritize_avoiding_fragmented_speech']
            else:
                preferSentenceEnd = True
            if considerNext and considerPrev and preferSentenceEnd == True:
                # If current doesn't end a sentence and next ends a sentence, combine with next
                if not ends_with_sentence_terminator(entryListLocal[i]['translated_text']) and ends_with_sentence_terminator(entryListLocal[i+1]['translated_text']):
                    combine_with_next()
                    noMorePossibleCombines = False
                    break
                # If current ends a sentence and previous doesn't, combine with previous
                elif ends_with_sentence_terminator(entryListLocal[i]['translated_text']) and not ends_with_sentence_terminator(entryListLocal[i-1]['translated_text']):
                    combine_with_prev()
                    noMorePossibleCombines = False
                    break
                # Check if previous ends a sentence, if so combine with next, unless current also ends a sentence
                elif ends_with_sentence_terminator(entryListLocal[i-1]['translated_text']) and not ends_with_sentence_terminator(entryListLocal[i]['translated_text']):
                    combine_with_next()
                    noMorePossibleCombines = False
                    break

            
            # Case where char_rate is lower than goal
            if data['char_rate'] > charRateGoal:
                # If both are to be considered, then choose the one with the lower char_rate.
                if considerNext and considerPrev:
                    # Choose lower char rate
                    if nextDiff < prevDiff:
                        combine_with_next()
                        noMorePossibleCombines = False
                        break
                    else:
                        combine_with_prev()
                        noMorePossibleCombines = False
                        break
                # If only one is to be considered, then combine with that one
                elif considerNext:
                    combine_with_next()
                    noMorePossibleCombines = False
                    break
                elif considerPrev:
                    combine_with_prev()
                    noMorePossibleCombines = False
                    break
                else:
                    print(f"Error U: Should not reach this point! Current entry = {i}")
                    print(f"Current Entry Text = {data['text']}")
                    continue
            
            # Case where char_rate is lower than goal
            elif data['char_rate'] < charRateGoal:
                # If both are to be considered, then choose the one with the higher char_rate.
                if considerNext and considerPrev:                  
                    # Choose higher char rate
                    if nextDiff > prevDiff:
                        combine_with_next()
                        noMorePossibleCombines = False
                        break
                    else:
                        combine_with_prev()
                        noMorePossibleCombines = False
                        break
                # If only one is to be considered, then combine with that one
                elif considerNext:
                    combine_with_next()
                    noMorePossibleCombines = False
                    break
                elif considerPrev:
                    combine_with_prev()
                    noMorePossibleCombines = False
                    break
                else:
                    print(f"Error L: Should not reach this point! Index = {i}")
                    print(f"Current Entry Text = {data['text']}")
                    continue
    return entryListLocal, noMorePossibleCombines

#-- End of combine_single_pass --    

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
