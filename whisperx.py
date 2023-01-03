import re
import subprocess
import os
import configparser

#---------------------------------------- Batch File Processing ----------------------------------------
batchConfig = configparser.ConfigParser()
batchConfig.read('batch.ini')

# MOVE THIS INTO A VARIABLE AT SOME POINT
outputFolder = "output"

# Get the video file name Create the output folder based on the original video file name
originalVideoFile = os.path.abspath(batchConfig['SETTINGS']['original_video_file_path'].strip("\""))

#whisperx (Whisper-Based Automatic Speech Recognition (ASR) with improved timestamp accuracy using forced alignment)
def transcribe(videoFile, output):
    #Catch the video file name and create a folder with the same name
    fileName = os.path.basename(videoFile).split(".")[0]
    fileName = re.sub(r"[^\w\s-]", "", fileName) #Remove special characters
    outputFolder = output + "/" + fileName

    #Create the output folder
    if not os.path.exists(outputFolder):
        os.makedirs(outputFolder)

    #Extract the audio from the original video to wav and save it in the output/{original_video_name}
    command = f"ffmpeg -i {videoFile} -vn -acodec pcm_s16le -ac 1 -ar 48000 -f wav {outputFolder}/original.wav"
    subprocess.call(command, shell=True)

    #If you want to install whisperx in another environment, use conda envs
    #os.system(f"conda activate whisperx && whisperx {outputFolder}/original.wav --model small.en --align_model WAV2VEC2_ASR_LARGE_LV60K_960H --output_dir {outputFolder}")
    #Run whisperx
    os.system(f"whisperx {outputFolder}/original.wav --model small.en --align_model WAV2VEC2_ASR_LARGE_LV60K_960H --output_dir {outputFolder}")

transcribe(originalVideoFile, outputFolder)