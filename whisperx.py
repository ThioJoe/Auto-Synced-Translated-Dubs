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
def transcribe(videoFile, outputFolder):
    #Create the output folder
    if not os.path.exists(outputFolder):
        os.makedirs(outputFolder)

    #If already exists, delete the original.wav file
    if os.path.exists(f"{outputFolder}/original.wav"):
        os.remove(f"{outputFolder}/original.wav")

    #Extract the audio from the original video to wav and save it in the output/{original_video_name}
    command = f"ffmpeg -i {videoFile} -vn -acodec pcm_s16le -ac 1 -ar 48000 -f wav {outputFolder}/original.wav"
    subprocess.call(command, shell=True)

    #If you want to install whisperx in another environment, use conda envs
    #os.system(f"conda activate {our_env} && whisperx...")
    #Run whisperx
    os.system(f"whisperx {outputFolder}/original.wav --model small.en --align_model WAV2VEC2_ASR_LARGE_LV60K_960H --output_dir {outputFolder}")
    #verify if the transcription is done
    if os.path.exists(f"{outputFolder}/original.wav.srt"):
        print(f"Transcription completed. The output file is in {outputFolder}/original.wav.srt")
    else:
        print(f"Transcription failed. Check the README.md file for more information about the whisperx installation.")

transcribe(originalVideoFile, outputFolder)
