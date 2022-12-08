import json
import base64
import os
import time
import configparser
from googleapiclient.errors import HttpError

import auth
TTS_API, TRANSLATE_API = auth.first_authentication()

# Read config file
config = configparser.ConfigParser()
config.read('config.ini')
# Get variables from config
audioEncoding = config['SETTINGS']['synth_audio_encoding'].upper()
languageCode = config['SETTINGS']['synth_language_code']
voiceName = config['SETTINGS']['synth_voice_name']
voiceGender = config['SETTINGS']['synth_voice_gender'].upper()

# Get List of Voices Available
def get_voices():
    voices = TTS_API.voices().list().execute()
    voices_json = json.dumps(voices)
    return voices_json

# Build API request for google text to speech, then execute
def synthesize_text(text, audioEncoding=audioEncoding, languageCode=languageCode, voiceName=voiceName, voiceGender=voiceGender,):
    # API Info at https://texttospeech.googleapis.com/$discovery/rest?version=v1
    # Try, if error regarding quota, waits a minute and tries again
    def send_request():
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
                    "audioEncoding": audioEncoding # MP3
                }
            }
        ).execute()
        return response

    # Use try except to catch quota errors, there is a limit of 100 requests per minute for neural2 voices
    try:
        response = send_request()
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

def synthesize_dictionary(subsDict, skipSynthesize=False):
    for key, value in subsDict.items():
        # TTS each subtitle text, write to file, write filename into dictionary
        filePath = f"workingFolder\\{key}.mp3"
        if not skipSynthesize:
            audio = synthesize_text(value['translated_text'])

            # If folder doesn't exist, create it
            if not os.path.exists(os.path.dirname(filePath)):
                try:
                    os.makedirs(os.path.dirname(filePath))
                except OSError:
                    print("Error creating directory")
            
            with open(filePath, "wb") as out:
                out.write(audio)

        subsDict[key]['TTS_FilePath'] = filePath

        # Print progress and overwrite line next time
        print(f" Synthesizing TTS Line: {key} of {len(subsDict)}", end="\r")
    print("                                               ") # Clear the line
    return subsDict
