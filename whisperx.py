# REMEMBER: Unlike the .ini config files, the variable values here must be surrounded by "quotation" marks

    # The video can be anywhere as long as you use the full absolute filepath. Or you can use a relative path.
    # This script assumes the video is an mp4 file. I'm not sure if it will work with other formats/containers.
originalVideoFile = r"folder\your_video.mp4"

    # Output base folder of the video transcription
    # The script will create a folder with the original video name inside the output folder
outputFolder = r"output"    

    # The model to use for the transcription. The default is "small.en".
    # Check the list of available models at https://github.com/openai/whisper
whisperModel = r"small.en"

    # The alignment model is used to improve the accuracy of the timestamps. The default is "WAV2VEC2_ASR_LARGE_LV60K_960H" for English only.
    # To use other languages, see https://github.com/m-bain/whisperX
whisperXAlignModel = r"WAV2VEC2_ASR_LARGE_LV60K_960H"

#========================================================================================================

import re
import subprocess
import os

# Create the output folder based on the original video file name
VideoFileName = os.path.basename(originalVideoFile).split(".")[0]
VideoFileName = re.sub(r"[^\w\s-]", "", VideoFileName) #Remove special characters
outputFolder = f"{outputFolder}/{VideoFileName}"

#whisperx (Whisper-Based Automatic Speech Recognition (ASR) with improved timestamp accuracy using forced alignment)
def transcribe(videoFile, outputFolder, Model, AlignModel):
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
    os.system(f"whisperx {outputFolder}/original.wav --model {Model} --align_model {AlignModel} --output_dir {outputFolder}")
    #verify if the transcription is done
    if os.path.exists(f"{outputFolder}/original.wav.srt"):
        print(f"Transcription completed. The output file is in {outputFolder}/original.wav.srt")
    else:
        print(f"Transcription failed. Check the README.md file for more information about the whisperx installation.")

transcribe(originalVideoFile, outputFolder, whisperModel, whisperXAlignModel)
