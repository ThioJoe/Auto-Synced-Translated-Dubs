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
OUTPUT_DIRECTORY = 'Outputs'
OUTPUT_FOLDER = os.path.join(OUTPUT_DIRECTORY , os.path.splitext(os.path.basename(ORIGINAL_VIDEO_PATH))[0])

# Fix original video path if debug mode
if config['debug_mode'] and (ORIGINAL_VIDEO_PATH == '' or ORIGINAL_VIDEO_PATH.lower() == 'none'):
    ORIGINAL_VIDEO_PATH = 'Debug.test'
else:
    ORIGINAL_VIDEO_PATH = os.path.abspath(ORIGINAL_VIDEO_PATH.strip("\""))

# ---------------------------------------------------------------------------------------
__all__ = ['os', 'sys', 'traceback', 'config', 'cloudConfig', 'batchConfig', 'ORIGINAL_VIDEO_PATH', 'OUTPUT_DIRECTORY', 'OUTPUT_FOLDER', 're', 'regex', 'parseBool']
