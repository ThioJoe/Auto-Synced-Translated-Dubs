import json
import base64
import os
import time
import configparser
import azure.cognitiveservices.speech as speechsdk
from googleapiclient.errors import HttpError

import auth
TTS_API, TRANSLATE_API = auth.first_authentication()

# Read config files
config = configparser.ConfigParser()
config.read('config.ini')
cloudConfig = configparser.ConfigParser()
cloudConfig.read('cloud_service_settings.ini')

# Get variables from config
ttsService = cloudConfig['CLOUD']['tts_service'].lower()
audioEncoding = config['SETTINGS']['synth_audio_encoding'].upper()

# Get Azure variables if applicable
AZURE_SPEECH_KEY = cloudConfig['CLOUD']['azure_speech_key']
AZURE_SPEECH_REGION = cloudConfig['CLOUD']['azure_speech_region']

# Get List of Voices Available
def get_voices():
    voices = TTS_API.voices().list().execute()
    voices_json = json.dumps(voices)
    return voices_json

# Build API request for google text to speech, then execute
def synthesize_text_google(text, speedFactor, voiceName, voiceGender, languageCode, audioEncoding=audioEncoding):
    # Keep speedFactor between 0.25 and 4.0
    if speedFactor < 0.25:
        speedFactor = 0.25
    elif speedFactor > 4.0:
        speedFactor = 4.0

    # API Info at https://texttospeech.googleapis.com/$discovery/rest?version=v1
    # Try, if error regarding quota, waits a minute and tries again
    def send_request(speedFactor):
        response = TTS_API.text().synthesize(
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

    # The response's audioContent is base64. Must decode to selected audio format
    decoded_audio = base64.b64decode(response['audioContent'])
    return decoded_audio

def synthesize_text_azure(text, speedFactor, voiceName, languageCode):
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

    # Create SSML syntax for Azure TTS
    ssml = f"<speak version='1.0' xml:lang='{languageCode}' xmlns='http://www.w3.org/2001/10/synthesis' " \
        "xmlns:mstts='http://www.w3.org/2001/mstts'>" \
        f"<voice name='{voiceName}'>" \
        f"<prosody rate='{rate}'>{text}</prosody></voice></speak>"

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


def synthesize_dictionary(subsDict, langDict, skipSynthesize=False, secondPass=False):
    for key, value in subsDict.items():
        # TTS each subtitle text, write to file, write filename into dictionary
        filePath = f"workingFolder\\{key}.mp3"
        if not skipSynthesize:

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
            if ttsService == "google":
                audio = synthesize_text_google(value['translated_text'], speedFactor, langDict['voiceName'], langDict['voiceGender'], langDict['languageCode'])
                with open(filePath, "wb") as out:
                    out.write(audio)

            # If Azure TTS, use Azure API
            elif ttsService == "azure":
                # Audio variable is an AudioDataStream object
                audio = synthesize_text_azure(value['translated_text'], speedFactor, langDict['voiceName'], langDict['languageCode'])
                # Save to file using save_to_wav_file method of audio object
                audio.save_to_wav_file(filePath)

        subsDict[key]['TTS_FilePath'] = filePath

        # Print progress and overwrite line next time
        if not secondPass:
            print(f" Synthesizing TTS Line: {key} of {len(subsDict)}", end="\r")
        else:
            print(f" Synthesizing TTS Line (2nd Pass): {key} of {len(subsDict)}", end="\r")
    print("                                               ") # Clear the line
    return subsDict
