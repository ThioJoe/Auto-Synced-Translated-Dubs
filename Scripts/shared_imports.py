import os
import sys
import traceback
import configparser
import re
import regex

from Scripts.utils import parseBool, parseConfigSetting

# Get Config Values
configRaw = configparser.ConfigParser()
configRaw.read('config.ini')

cloudConfigRaw = configparser.ConfigParser()
cloudConfigRaw.read('cloud_service_settings.ini')

batchConfig = configparser.ConfigParser()
batchConfig.read('batch.ini') # Don't process this one, need sections in tact for languages

# Go through all the config files, convert to dictionary
config = {}
cloudConfig = {}

for section in configRaw.sections():
    for key in configRaw[section]:
        config[key] = parseConfigSetting(configRaw[section][key])

for section in cloudConfigRaw.sections():
    for key in cloudConfigRaw[section]:
        cloudConfig[key] = parseConfigSetting(cloudConfigRaw[section][key])

# ----- Create constants ------
ORIGINAL_VIDEO_PATH = batchConfig['SETTINGS']['original_video_file_path']
ORIGINAL_VIDEO_NAME = os.path.splitext(os.path.basename(ORIGINAL_VIDEO_PATH))[0]
OUTPUT_DIRECTORY = 'Outputs'
OUTPUT_YTSYNCED_DIRECTORY = 'YouTube Auto-Synced Subtitles'
OUTPUT_FOLDER = os.path.join(OUTPUT_DIRECTORY , ORIGINAL_VIDEO_NAME)
OUTPUT_YTSYNCED_FOLDER = os.path.join(OUTPUT_FOLDER, OUTPUT_YTSYNCED_DIRECTORY)

# Fix original video path if debug mode
if config['debug_mode'] and (ORIGINAL_VIDEO_PATH == '' or ORIGINAL_VIDEO_PATH.lower() == 'none'):
    ORIGINAL_VIDEO_PATH = 'Debug.test'
else:
    ORIGINAL_VIDEO_PATH = os.path.abspath(ORIGINAL_VIDEO_PATH.strip("\""))

# ---------------------------------------------------------------------------------------
__all__ = ['os', 'sys', 'traceback', 'config', 'cloudConfig', 'batchConfig', 'ORIGINAL_VIDEO_PATH', 'ORIGINAL_VIDEO_NAME', 'OUTPUT_DIRECTORY', 'OUTPUT_YTSYNCED_DIRECTORY', 'OUTPUT_FOLDER', 'OUTPUT_YTSYNCED_FOLDER', 're', 'regex', 'parseBool']
