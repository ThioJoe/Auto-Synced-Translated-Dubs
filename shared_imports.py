import os
import sys
import traceback
import configparser

from utils import parseBool

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
        config[key] = parseBool(configRaw[section][key], silent=True)

for section in cloudConfigRaw.sections():
    for key in cloudConfigRaw[section]:
        cloudConfig[key] = parseBool(cloudConfigRaw[section][key], silent=True)

__all__ = ['os', 'sys', 'traceback', 'config', 'cloudConfig', 'batchConfig']
