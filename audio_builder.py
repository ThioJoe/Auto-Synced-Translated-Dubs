import pydub
import librosa
import numpy as np
import soundfile
import pyrubberband
import configparser
import pathlib
import os

import TTS
from utils import parseBool

from pydub import AudioSegment
from pydub.silence import detect_leading_silence

# Set working folder
workingFolder = "workingFolder"

# Read config file
config = configparser.ConfigParser()
config.read('config.ini')
# Get variables from config
nativeSampleRate = int(config['SETTINGS']['synth_sample_rate'])
originalVideoFile = os.path.abspath(config['SETTINGS']['original_video_file_path'].strip("\""))
skipSynthesize = parseBool(config['SETTINGS']['skip_synthesize'])
forceTwoPassStretch = parseBool(config['SETTINGS']['force_stretch_with_twopass'])

# Use video file name to use in the name of the output file
outputFileName = pathlib.Path(originalVideoFile).stem + " - Output.wav"

def trim_clip(inputSound):
    trim_leading_silence: AudioSegment = lambda x: x[detect_leading_silence(x) :]
    trim_trailing_silence: AudioSegment = lambda x: trim_leading_silence(x.reverse()).reverse()
    strip_silence: AudioSegment = lambda x: trim_trailing_silence(trim_leading_silence(x))
    strippedSound = strip_silence(inputSound)
    return strippedSound

# Function to insert audio into canvas at specific point
def insert_audio(canvas, audioToOverlay, startTimeMs):
    # Create a copy of the canvas
    canvasCopy = canvas
    # Overlay the audio onto the copy
    canvasCopy = canvasCopy.overlay(audioToOverlay, position=int(startTimeMs))
    # Return the copy
    return canvasCopy

# Function to create a canvas of a specific duration in miliseconds
def create_canvas(canvasDuration, frame_rate=nativeSampleRate):
    canvas = AudioSegment.silent(duration=canvasDuration, frame_rate=frame_rate)
    return canvas

def get_speed_factor(subsDict, trimmedAudioPath, desiredDuration, num):
    rawDuration = librosa.get_duration(filename=trimmedAudioPath)
    # Calculate the speed factor, put into dictionary
    desiredDuration = float(desiredDuration)
    speedFactor = (rawDuration*1000) / desiredDuration
    subsDict[num]['speed_factor'] = speedFactor
    return subsDict

def stretch_audio(audioFileToStretch, speedFactor, num):
    y, sampleRate = soundfile.read(audioFileToStretch)
    streched_audio = pyrubberband.time_stretch(y, sampleRate, speedFactor, rbargs={'--fine': '--fine'}) # Need to add rbarges in weird way because it demands a dictionary of two values
    soundfile.write(f'{workingFolder}\\temp_stretched.wav', streched_audio, sampleRate)
    #soundfile.write(f'{workingFolder}\\{num}_s.wav', streched_audio, sampleRate) # For debugging, saves the stretched audio files
    return AudioSegment.from_file(f'{workingFolder}\\temp_stretched.wav', format="wav")


def build_audio(subsDict, totalAudioLength, twoPassVoiceSynth=False):
    # First trim silence off the audio files
    for key, value in subsDict.items():
        filePathTrimmed = workingFolder + "\\" + key + "_t.wav"
        subsDict[key]['TTS_FilePath_Trimmed'] = filePathTrimmed

        # Trim the clip and re-write file
        rawClip = AudioSegment.from_file(value['TTS_FilePath'], format="mp3", frame_rate=nativeSampleRate)
        trimmedClip = trim_clip(rawClip)
        trimmedClip.export(filePathTrimmed, format="wav")
        print(f" Trimmed Audio: {key} of {len(subsDict)}", end="\r")
    print("\n")

    # Calculate speed factors for each clip, aka how much to stretch the audio
    for key, value in subsDict.items():
        subsDict = get_speed_factor(subsDict, value['TTS_FilePath_Trimmed'], value['duration_ms'], num=key)
        print(f" Calculated Speed Factor: {key} of {len(subsDict)}", end="\r")
    print("\n")

    # If two pass voice synth is enabled, have API re-synthesize the clips at the new speed
    if twoPassVoiceSynth == True:
        subsDict = TTS.synthesize_dictionary(subsDict, skipSynthesize=skipSynthesize, secondPass=True)
        for key, value in subsDict.items():
            # Trim the clip and re-write file
            rawClip = AudioSegment.from_file(value['TTS_FilePath'], format="mp3", frame_rate=nativeSampleRate)
            trimmedClip = trim_clip(rawClip)
            trimmedClip.export(value['TTS_FilePath_Trimmed'], format="wav")
            print(f" Trimmed Audio (2nd Pass): {key} of {len(subsDict)}", end="\r")
        print("\n")
        for key, value in subsDict.items():
            subsDict = get_speed_factor(subsDict, value['TTS_FilePath_Trimmed'], value['duration_ms'], num=key)
            print(f" Calculated Speed Factor (2nd Pass): {key} of {len(subsDict)}", end="\r")
        print("\n")

    # Create canvas to overlay audio onto
    canvas = create_canvas(totalAudioLength)    

    # Stretch audio and insert into canvas
    for key, value in subsDict.items():
        if not twoPassVoiceSynth or forceTwoPassStretch == True:
            stretchedClip = stretch_audio(value['TTS_FilePath_Trimmed'], speedFactor=subsDict[key]['speed_factor'], num=key)
        else:
            stretchedClip = AudioSegment.from_file(value['TTS_FilePath_Trimmed'], format="wav")

        canvas = insert_audio(canvas, stretchedClip, value['start_ms'])
        print(f" Stretched Audio: {key} of {len(subsDict)}", end="\r")
    print("\n")

    canvas.export(outputFileName, format="wav")

    return subsDict
