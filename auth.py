#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Google Authentication Modules
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Other Modules
import os
import sys
import traceback
from json import JSONDecodeError
import configparser
import deepl

# Import Configs
cloudConfig = configparser.ConfigParser()
cloudConfig.read('cloud_service_settings.ini')

# Google Cloud Globals
token_file_name = 'token.pickle'
youtube_token_filename = 'yt_token.pickle'
GOOGLE_TTS_API = None
GOOGLE_TRANSLATE_API = None

# deepl Globals
DEEPL_API = None

#################################################################################################
################################## GOOGLE AUTHORIZATION #########################################
#################################################################################################
# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the {{ Google Cloud Console }} at https://cloud.google.com/console
# Please ensure that you have enabled the Text to Speech API for your project.
# For more information about the client_secrets.json file format, see:
# https://developers.google.com/api-client-library/python/guide/aaa_client_secrets

# Authorize the request and store authorization credentials.
def get_authenticated_service(youtubeAuth = False):
  global GOOGLE_TTS_API
  global GOOGLE_TRANSLATE_API
  CLIENT_SECRETS_FILE = 'client_secrets.json'
  YOUTUBE_CLIENT_SECRETS_FILE = 'yt_client_secrets.json'
  GOOGLE_API_SCOPES = ['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/cloud-translation']
  
  # TTS API Info
  GOOGLE_TTS_API_SERVICE_NAME = 'texttospeech'
  GOOGLE_TTS_API_VERSION = 'v1'
  TTS_DISCOVERY_SERVICE_URL = "https://texttospeech.googleapis.com/$discovery/rest?version=v1"

  # Translate API Info
  # https://translate.googleapis.com/$discovery/rest?version=v3 # v3 or beta v3beta1
  GOOGLE_TRANSLATE_API_SERVICE_NAME = 'translate'
  GOOGLE_TRANSLATE_API_VERSION = 'v3beta1'
  TRANSLATE_DISCOVERY_SERVICE_URL = "https://translate.googleapis.com/$discovery/rest?version=v3beta1"

  # YouTube API Info
  YT_READ_WRITE_SSL_SCOPE = ['https://www.googleapis.com/auth/youtube.force-ssl']
  YT_API_SERVICE_NAME = 'youtube'
  YT_API_VERSION = 'v3'
  YT_DISCOVERY_SERVICE_URL = "https://youtube.googleapis.com/$discovery/rest?version=v3"

  # Set proper variables based on which API is being used
  if youtubeAuth:
    API_SCOPES = YT_READ_WRITE_SSL_SCOPE
  else:
    API_SCOPES = GOOGLE_API_SCOPES

  if youtubeAuth == True:
    token_file = youtube_token_filename
  else:
    token_file = token_file_name

  if youtubeAuth == True:
    secrets_file = YOUTUBE_CLIENT_SECRETS_FILE
  else:
    secrets_file = CLIENT_SECRETS_FILE

  # Check if client_secrets.json file exists, if not give error
  if not os.path.exists(secrets_file):
    # In case people don't have file extension viewing enabled, they may add a redundant json extension
    if os.path.exists(f"{secrets_file}.json"):
      secrets_file = secrets_file + ".json"
    else:
      print(f"\n         ----- [!] Error: client_secrets.json file not found -----")
      print(f" ----- Did you create a Google Cloud Platform Project to access the API? ----- ")
      input("\nPress Enter to Exit...")
      sys.exit()

  creds = None
  # The file token.pickle stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first time.
  if os.path.exists(token_file):
    creds = Credentials.from_authorized_user_file(token_file, scopes=API_SCOPES)

  # If there are no (valid) credentials available, make the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      print(f"\nPlease login using the browser window that opened just now.\n")
      flow = InstalledAppFlow.from_client_secrets_file(secrets_file, scopes=API_SCOPES)
      creds = flow.run_local_server(port=0, authorization_prompt_message="Waiting for authorization. See message above.")
      print(f"[OK] Authorization Complete.")
      # Save the credentials for the next run
    with open(token_file, 'w') as token:
      token.write(creds.to_json())
  
  if youtubeAuth:
    # Build YouTube API object
    YOUTUBE_API =  build(YT_API_SERVICE_NAME, YT_API_VERSION, credentials=creds, discoveryServiceUrl=YT_DISCOVERY_SERVICE_URL)
    return YOUTUBE_API

  # Build tts and translate API objects    
  GOOGLE_TTS_API = build(GOOGLE_TTS_API_SERVICE_NAME, GOOGLE_TTS_API_VERSION, credentials=creds, discoveryServiceUrl=TTS_DISCOVERY_SERVICE_URL)
  GOOGLE_TRANSLATE_API = build(GOOGLE_TRANSLATE_API_SERVICE_NAME, GOOGLE_TRANSLATE_API_VERSION, credentials=creds, discoveryServiceUrl=TRANSLATE_DISCOVERY_SERVICE_URL)
  
  return GOOGLE_TTS_API, GOOGLE_TRANSLATE_API

def youtube_authentication():
  global YOUTUBE_API
  try:
    YOUTUBE_API = get_authenticated_service(youtubeAuth = True) # Create authentication object
  except JSONDecodeError as jx:
    print(f" [!!!] Error: " + str(jx))
    print(f"\nDid you make the client_secrets.json file yourself by copying and pasting into it, instead of downloading it?")

    input("Press Enter to Exit...")
    sys.exit()
  except Exception as e:
    if "invalid_grant" in str(e):
      print(f"[!] Invalid token - Requires Re-Authentication")
      os.remove(youtube_token_filename)
      youtube_authentication()
    else:
      print(f" [!!!] Error: " + str(e))
      input("Press Enter to Exit...")
      sys.exit()
  return YOUTUBE_API

def first_authentication():
  global GOOGLE_TTS_API, GOOGLE_TRANSLATE_API
  try:
    GOOGLE_TTS_API, GOOGLE_TRANSLATE_API = get_authenticated_service() # Create authentication object
  except JSONDecodeError as jx:
    print(f" [!!!] Error: " + str(jx))
    print(f"\nDid you make the yt_client_secrets.json file yourself by copying and pasting into it, instead of downloading it?")
    print(f"You need to download the json file directly from the Google Cloud dashboard, by creating credentials.")
    input("Press Enter to Exit...")
    sys.exit()
  except Exception as e:
    if "invalid_grant" in str(e):
      print(f"[!] Invalid token - Requires Re-Authentication")
      os.remove(token_file_name)
      GOOGLE_TTS_API, GOOGLE_TRANSLATE_API = get_authenticated_service()
    else:
      print('\n')
      traceback.print_exc() # Prints traceback
      print("----------------")
      print(f"[!!!] Error: " + str(e))
      input(f"\nError: Something went wrong during authentication. Try deleting the token.pickle file. \nPress Enter to Exit...")
      sys.exit()
  return GOOGLE_TTS_API, GOOGLE_TRANSLATE_API


################################################################################################
################################## DEEPL AUTHORIZATION #########################################
################################################################################################

def deepl_auth():
  # Deepl API Key
  deeplApiKey = cloudConfig['CLOUD']['deepl_api_key']
  deepl_auth_object = deepl.Translator(deeplApiKey)
  return deepl_auth_object

if cloudConfig['CLOUD']['translate_service'] == 'deepl':
  DEEPL_API = deepl_auth()