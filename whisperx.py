import re
import subprocess
import os
import configparser

#---------------------------------------- Batch File Processing ----------------------------------------
batchConfig = configparser.ConfigParser()
batchConfig.read('batch.ini')
originalVideoFile = os.path.abspath(batchConfig['SETTINGS']['original_video_file_path'].strip("\""))

# MOVE THIS INTO A VARIABLE AT SOME POINT
outputFolder = "output"

# Get the video file name Create the output folder based on the original video file name
originalVideoFile = os.path.abspath(batchConfig['SETTINGS']['original_video_file_path'].strip("\""))

