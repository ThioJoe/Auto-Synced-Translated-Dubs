import json
import base64
import os
import time
import configparser
import azure.cognitiveservices.speech as speechsdk
from googleapiclient.errors import HttpError
import datetime
import zipfile
import io
import copy
import re
from urllib.request import urlopen

from Scripts.shared_imports import *
import Scripts.auth as auth
import Scripts.azure_batch as azure_batch
import Scripts.utils as utils
from Scripts.utils import parseBool

# Get variables from config

# Get Azure variables if applicable
AZURE_SPEECH_KEY = cloudConfig['azure_speech_key']
AZURE_SPEECH_REGION = cloudConfig['azure_speech_region']

# Get List of Voices Available
def get_voices():
    voices = auth.GOOGLE_TTS_API.voices().list().execute()
    voices_json = json.dumps(voices)
    return voices_json


# ======================================== Pronunciation Correction Functions ================================================

interpretAsOverrideFile = os.path.join('SSML_Customization', 'interpret-as.csv')
interpretAsEntries = utils.csv_to_dict(interpretAsOverrideFile)

aliasOverrideFile = os.path.join('SSML_Customization', 'aliases.csv')
aliasEntries = utils.csv_to_dict(aliasOverrideFile)

urlListFile = os.path.join('SSML_Customization', 'url_list.txt')
urlList = utils.txt_to_list(urlListFile)

phonemeFile = os.path.join('SSML_Customization', 'Phoneme_Pronunciation.csv')
phonemeEntries = utils.csv_to_dict(phonemeFile)

def add_all_pronunciation_overrides(text):
    text = add_interpretas_tags(text)
    text = add_alias_tags(text)
    text = add_phoneme_tags(text)
    return text

def add_interpretas_tags(text):
    # Add interpret-as tags from interpret-as.csv
    for entryDict in interpretAsEntries:
        # Get entry info
        entryText = entryDict['Text']
        entryInterpretAsType = entryDict['interpret-as Type']
        isCaseSensitive = parseBool(entryDict['Case Sensitive (True/False)'])
        entryFormat = entryDict['Format (Optional)']

        # Create say-as tag
        if entryFormat == "":
            sayAsTagStart = rf'<say-as interpret-as="{entryInterpretAsType}">'
        else:
            sayAsTagStart = rf'<say-as interpret-as="{entryInterpretAsType}" format="{entryFormat}">'
        
        # Find and replace the word
        findWordRegex = rf'(\b["\']?{entryText}[.,!?]?["\']?\b)' # Find the word, with optional punctuation after, and optional quotes before or after
        if isCaseSensitive:
            text = re.sub(findWordRegex, rf'{sayAsTagStart}\1</say-as>', text) # Uses group reference, so remember regex must be in parentheses
            
        else:
            text = re.sub(findWordRegex, rf'{sayAsTagStart}\1</say-as>', text, flags=re.IGNORECASE)

    # Add interpret-as tags from url_list.txt
    for url in urlList:
        # This regex expression will match the top level domain extension, and the punctuation before/after it, and any periods, slashes or colons
        # It will then put the say-as characters tag around all matches
        punctuationRegex = re.compile(r'((?:\.[a-z]{2,6}(?:\/|$|\s))|(?:[\.\/:]+))') 
        taggedURL = re.sub(punctuationRegex, r'<say-as interpret-as="characters">\1</say-as>', url)
        # Replace any instances of the URL with the tagged version
        text = text.replace(url, taggedURL)

    return text

def add_alias_tags(text):
    for entryDict in aliasEntries:
        # Get entry info
        entryText = entryDict['Original Text']
        entryAlias = entryDict['Alias']
        if entryDict['Case Sensitive (True/False)'] == "":
            isCaseSensitive = False
        else:
            isCaseSensitive = parseBool(entryDict['Case Sensitive (True/False)'])

        # Find and replace the word
        findWordRegex = rf'\b["\'()]?{entryText}[.,!?()]?["\']?\b' # Find the word, with optional punctuation after, and optional quotes before or after
        if isCaseSensitive:
            text = re.sub(findWordRegex, rf'{entryAlias}', text)
        else:
            text = re.sub(findWordRegex, rf'{entryAlias}', text, flags=re.IGNORECASE)
    return text


# Uses the phoneme pronunciation file to add phoneme tags to the text
def add_phoneme_tags(text):
    for entryDict in phonemeEntries:
        # Get entry info
        entryText = entryDict['Text']
        entryPhoneme = entryDict['Phonetic Pronunciation']
        entryAlphabet = entryDict['Phonetic Alphabet']

        if entryDict['Case Sensitive (True/False)'] == "":
            isCaseSensitive = False
        else:
            isCaseSensitive = parseBool(entryDict['Case Sensitive (True/False)'])

        # Find and replace the word
        findWordRegex = rf'(\b["\'()]?{entryText}[.,!?()]?["\']?\b)' # Find the word, with optional punctuation after, and optional quotes before or after
        if isCaseSensitive:
            text = re.sub(findWordRegex, rf'<phoneme alphabet="ipa" ph="{entryPhoneme}">\1</phoneme>', text)
        else:
            text = re.sub(findWordRegex, rf'<phoneme alphabet="{entryAlphabet}" ph="{entryPhoneme}">\1</phoneme>', text, flags=re.IGNORECASE)
    return text


# =============================================================================================================================

# Build API request for google text to speech, then execute
def synthesize_text_google(text, speedFactor, voiceName, voiceGender, languageCode, audioEncoding=config['synth_audio_encoding'].upper()):

    # Keep speedFactor between 0.25 and 4.0
    if speedFactor < 0.25:
        speedFactor = 0.25
    elif speedFactor > 4.0:
        speedFactor = 4.0

    # API Info at https://texttospeech.googleapis.com/$discovery/rest?version=v1
    # Try, if error regarding quota, waits a minute and tries again
    def send_request(speedFactor):
        response = auth.GOOGLE_TTS_API.text().synthesize(
            body={
                'input':{
                    "text": text
                },
                'voice':{
                    "languageCode":languageCode, # en-US
                    "ssmlGender": voiceGender, # MALE
                    "name": voiceName # "en-US-Neural2-I"
                },
                'audioConfig':{
                    "audioEncoding": audioEncoding, # MP3
                    "speakingRate": speedFactor
                }
            }
        ).execute()
        return response

    # Use try except to catch quota errors, there is a limit of 100 requests per minute for neural2 voices
    try:
        response = send_request(speedFactor)
    except HttpError as hx:
        print("Error Message: " + str(hx))
        if "Resource has been exhausted" in str(hx):
            # Wait 65 seconds, then try again
            print("Waiting 65 seconds to try again")
            time.sleep(65)
            print("Trying again...")
            response = send_request()
        else:
            input("Press Enter to continue...")
    except Exception as ex:
        print("Error Message: " + str(ex))
        input("Press Enter to continue...")


    # The response's audioContent is base64. Must decode to selected audio format
    decoded_audio = base64.b64decode(response['audioContent'])
    return decoded_audio

def synthesize_text_azure(text, duration, voiceName, languageCode):

    # Create tag for desired duration of clip
    durationTag = f'<mstts:audioduration value="{str(duration)}ms"/>'

    # Create string for sentence pauses, if not default
    if not config['azure_sentence_pause'] == 'default':
        sentencePauseTag = f'<mstts:silence type="Sentenceboundary-exact" value="{str(config["azure_sentence_pause"])}ms"/>'
    else:
        sentencePauseTag = ''

    # Create string for comma pauses, if not default
    if not config['azure_comma_pause'] == 'default':
        commaPauseTag = f'<mstts:silence type="Comma-exact" value="{str(config["azure_comma_pause"])}ms"/>'
    else:
        commaPauseTag = ''

    # Set string for tag to set leading and trailing silence times to zero
    leadSilenceTag = '<mstts:silence  type="Leading-exact" value="0ms"/>'
    tailSilenceTag = '<mstts:silence  type="Tailing-exact" value="0ms"/>'

    # Process text using pronunciation customization set by user
    text = add_all_pronunciation_overrides(text)

    # Create SSML syntax for Azure TTS
    ssml = f"<speak version='1.0' xml:lang='{languageCode}' xmlns='http://www.w3.org/2001/10/synthesis' " \
        "xmlns:mstts='http://www.w3.org/2001/mstts'>" \
        f"<voice name='{voiceName}'>{sentencePauseTag}{commaPauseTag}{durationTag}{leadSilenceTag}{tailSilenceTag}" \
        f"{text}</voice></speak>"

    speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
    # For Azure voices, see: https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/language-support?tabs=stt-tts
    speech_config.speech_synthesis_voice_name=voiceName
    # For audio outputs, see: https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.speechsynthesisoutputformat?view=azure-python
    speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

    #result = synthesizer.speak_text_async(text).get()
    result = synthesizer.speak_ssml_async(ssml).get()
    
    stream = speechsdk.AudioDataStream(result)
    return stream

def format_percentage_change(speedFactor):
    # Determine speedFactor value for Azure TTS. It should be either 'default' or a relative change.
    if speedFactor == 1.0:
        rate = 'default'
    else:
        # Whether to add a plus sign to the number to relative change. A negative will automatically be added
        if speedFactor >= 1.0:
            percentSign = '+'
        else:
            percentSign = ''
        # Convert speedFactor float value to a relative percentage    
        rate = percentSign + str(round((speedFactor - 1.0) * 100, 5)) + '%'
    return rate

def synthesize_text_azure_batch(subsDict, langDict, skipSynthesize=False, secondPass=False):

    def create_request_payload(remainingEntriesDict):
        # Create SSML for all subtitles
        ssmlJson = []
        payloadSizeInBytes = 0
        tempDict = dict(remainingEntriesDict) # Need to do this to avoid changing the original dict which would mess with the loop

        for key, value in tempDict.items():
            text = tempDict[key]['translated_text']
            duration = tempDict[key]['duration_ms_buffered']
            language = langDict['languageCode']
            voice = langDict['voiceName']

            # Create tag for desired duration of clip
            durationTag = f'<mstts:audioduration value="{str(duration)}ms"/>'

            # Create string for sentence pauses, if not default
            if not config['azure_sentence_pause'] == 'default':
                sentencePauseTag = f'<mstts:silence type="Sentenceboundary-exact" value="{str(config["azure_sentence_pause"])}ms"/>'
            else:
                sentencePauseTag = ''

            # Create string for comma pauses, if not default
            if not config['azure_comma_pause'] == 'default':
                commaPauseTag = f'<mstts:silence type="Comma-exact" value="{str(config["azure_comma_pause"])}ms"/>'
            else:
                commaPauseTag = ''

            # Set string for tag to set leading and trailing silence times to zero
            leadSilenceTag = '<mstts:silence  type="Leading-exact" value="0ms"/>'
            tailSilenceTag = '<mstts:silence  type="Tailing-exact" value="0ms"/>'    

            # Process text using pronunciation customization set by user
            text = add_all_pronunciation_overrides(text)

            # Create the SSML for each subtitle
            ssml = f"<speak version='1.0' xml:lang='{language}' xmlns='http://www.w3.org/2001/10/synthesis' " \
            "xmlns:mstts='http://www.w3.org/2001/mstts'>" \
            f"<voice name='{voice}'>{sentencePauseTag}{commaPauseTag}{durationTag}{leadSilenceTag}{tailSilenceTag}" \
            f"{text}</voice></speak>"
            ssmlJson.append({"text": ssml})

            # Construct request payload with SSML
            # Reconstruct payload with every loop with new SSML so that the payload size is accurate
            now = datetime.datetime.now()
            pendingPayload = {
                'displayName': langDict['languageCode'] + '-' + now.strftime("%Y-%m-%d %H:%M:%S"),
                'description': 'Batch synthesis of ' + langDict['languageCode'] + ' subtitles',
                "textType": "SSML",
                # To use custom voice, see original example code script linked from azure_batch.py
                "inputs": ssmlJson,
                "properties": {
                    "outputFormat": "audio-48khz-192kbitrate-mono-mp3",
                    "wordBoundaryEnabled": False,
                    "sentenceBoundaryEnabled": False,
                    "concatenateResult": False,
                    "decompressOutputFiles": False
                },
            }
            # Azure TTS Batch requests require payload must be under 500 kilobytes, so check payload is under 500,000 bytes. Not sure if they actually mean kibibytes, assume worst case.
            # Payload will be formatted as json so must account for that too by doing json.dumps(), otherwise calculated size will be inaccurate
            payloadSizeInBytes = len(str(json.dumps(pendingPayload)).encode('utf-8')) 

            if payloadSizeInBytes > 495000 or len(ssmlJson) > 995: # Leave some room for anything unexpected. Also number of inputs must be below 1000
                # If payload would be too large, ignore the last entry and break out of loop
                return payload, remainingEntriesDict
            else:
                payload = copy.deepcopy(pendingPayload) # Must make deepycopy otherwise ssmlJson will be updated in both instead of just pendingPayload
                # Remove entry from remainingEntriesDict if it was added to payload
                remainingEntriesDict.pop(key)                


        # If all the rest of the entries fit, return the payload
        return payload, remainingEntriesDict
    # ------------------------- End create_request_payload() -----------------------------------


    # Create payloads, split into multiple if necessary
    payloadList = []
    remainingPayloadEntriesDict = dict(subsDict) # Will remove entries as they are added to payloads
    while len(remainingPayloadEntriesDict) > 0:
        payloadToAppend, remainingPayloadEntriesDict = create_request_payload(remainingPayloadEntriesDict)
        payloadList.append(payloadToAppend)
    
    # Tell user if request will be broken up into multiple payloads
    if len(payloadList) > 1:
        print(f'Payload will be broken up into {len(payloadList)} requests (due to Azure size limitations).')

    # Use to keep track of filenames downloaded via separate zip files. WIll remove as they are downloaded
    remainingDownloadedEntriesList = list(subsDict.keys())

    # Clear out workingFolder
    for filename in os.listdir('workingFolder'):
        if not config['debug_mode']:
            os.remove(os.path.join('workingFolder', filename))

    # Loop through payloads and submit to Azure
    for payload in payloadList:
        # Reset job_id from previous loops
        job_id = None
        
        # Send request to Azure
        job_id = azure_batch.submit_synthesis(payload)

        # Wait for job to finish
        if job_id is not None:
            status = "Running"
            resultDownloadLink = None
            
            while True: # Must use break to exit loop
                # Get status
                response = azure_batch.get_synthesis(job_id)
                status = response.json()['status']
                if status == 'Succeeded':
                    print('Batch synthesis job succeeded')
                    resultDownloadLink = azure_batch.get_synthesis(job_id).json()['outputs']['result']
                    break
                elif status == 'Failed':
                    print('ERROR: Batch synthesis job failed!')
                    print("Reason:" + response.reason)
                    break
                else:
                    print(f'Waiting for Azure batch synthesis job to finish. Status: [{status}]')
                    time.sleep(5)
            
            # Download resultig zip file
            if resultDownloadLink is not None:
                # Download zip file
                urlResponse = urlopen(resultDownloadLink)

                # If debug mode, save zip file to disk
                if config['debug_mode']:
                    if secondPass == False:
                        zipName = 'azureBatch.zip'
                    else:
                        zipName = 'azureBatchPass2.zip'

                    zipPath = os.path.join('workingFolder', zipName)
                    with open(zipPath, 'wb') as f:
                        f.write(urlResponse.read())
                    # Reset urlResponse so it can be read again
                    urlResponse = urlopen(resultDownloadLink)

                # Process zip file    
                virtualResultZip = io.BytesIO(urlResponse.read())
                zipdata = zipfile.ZipFile(virtualResultZip)
                zipinfos = zipdata.infolist()

                # Reorder zipinfos so the file names are in alphanumeric order
                zipinfos.sort(key=lambda x: x.filename)

                # Only extract necessary files, and rename them while doing so
                for file in zipinfos:
                    if file.filename == "summary.json":
                        #zipdata.extract(file, 'workingFolder') # For debugging
                        pass
                    elif "json" not in file.filename:
                        # Rename file to match first entry in remainingDownloadedEntriesDict, then extract
                        currentFileNum = remainingDownloadedEntriesList[0]
                        file.filename = str(currentFileNum) + '.mp3'
                        #file.filename = file.filename.lstrip('0')

                        # Add file path to subsDict then remove from remainingDownloadedEntriesList
                        subsDict[currentFileNum]['TTS_FilePath'] = os.path.join('workingFolder', str(currentFileNum)) + '.mp3'
                        # Extract file
                        zipdata.extract(file, 'workingFolder')
                        # Remove entry from remainingDownloadedEntriesList
                        remainingDownloadedEntriesList.pop(0)
                    

    return subsDict


def synthesize_dictionary_batch(subsDict, langDict, skipSynthesize=False, secondPass=False):
    if not skipSynthesize:
        if cloudConfig['tts_service'] == 'azure':
            subsDict = synthesize_text_azure_batch(subsDict, langDict, skipSynthesize, secondPass)
        else:
            print('ERROR: Batch TTS only supports azure at this time')
            input('Press enter to exit...')
            exit()
    return subsDict

def synthesize_dictionary(subsDict, langDict, skipSynthesize=False, secondPass=False):
    for key, value in subsDict.items():
        # TTS each subtitle text, write to file, write filename into dictionary
        filePath = os.path.join('workingFolder', f'{str(key)}.mp3')
        filePathStem = os.path.join('workingFolder', f'{str(key)}')
        if not skipSynthesize:

            duration = value['duration_ms_buffered']

            if secondPass:
                # Get speed factor from subsDict
                speedFactor = subsDict[key]['speed_factor']
            else:
                speedFactor = float(1.0)

            # Prepare output location. If folder doesn't exist, create it
            if not os.path.exists(os.path.dirname(filePath)):
                try:
                    os.makedirs(os.path.dirname(filePath))
                except OSError:
                    print("Error creating directory")

            # If Google TTS, use Google API
            if cloudConfig['tts_service'] == "google":
                audio = synthesize_text_google(value['translated_text'], speedFactor, langDict['voiceName'], langDict['voiceGender'], langDict['languageCode'])
                with open(filePath, "wb", encoding='utf-8') as out:
                    out.write(audio)
                
                # If debug mode, write to files after Google TTS
                if config['debug_mode'] and secondPass == False:
                    with open(filePathStem+"_p1.mp3", "wb", encoding='utf-8') as out:
                        out.write(audio)
                elif config['debug_mode'] and secondPass == True:
                    with open(filePathStem+"_p2.mp3", "wb", encoding='utf-8') as out:
                        out.write(audio)

            # If Azure TTS, use Azure API
            elif cloudConfig['tts_service'] == "azure":
                # Audio variable is an AudioDataStream object
                audio = synthesize_text_azure(value['translated_text'], duration, langDict['voiceName'], langDict['languageCode'])
                # Save to file using save_to_wav_file method of audio object
                audio.save_to_wav_file(filePath)
                
                # If debug mode, write to files after Google TTS
                if config['debug_mode'] and secondPass == False:
                    audio.save_to_wav_file(filePathStem+"_p1.mp3")
                elif config['debug_mode'] and secondPass == True:
                    audio.save_to_wav_file(filePathStem+"_p2.mp3")

        subsDict[key]['TTS_FilePath'] = filePath

        # Get key index
        keyIndex = list(subsDict.keys()).index(key)
        # Print progress and overwrite line next time
        if not secondPass:
            print(f" Synthesizing TTS Line: {keyIndex+1} of {len(subsDict)}", end="\r")
        else:
            print(f" Synthesizing TTS Line (2nd Pass): {keyIndex+1} of {len(subsDict)}", end="\r")
    print("                                               ") # Clear the line
    return subsDict
