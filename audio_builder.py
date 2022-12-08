import pydub
import librosa
import numpy as np
import soundfile
import pyrubberband

from pydub import AudioSegment
from pydub.silence import detect_leading_silence

# Set working folder
workingFolder = "workingFolder"
# Native Sample Rate of TTS
nativeSampleRate = 24000

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


def stretch_audio(subsDict, audioFileToStretch, desiredDuration, num):
    rawDuration = librosa.get_duration(filename=audioFileToStretch)
    # Calculate the stretch factor
    desiredDuration = float(desiredDuration)
    speedFactor = (rawDuration*1000) / desiredDuration
    subsDict[num]['speedFactor'] = speedFactor

    y, sampleRate = soundfile.read(audioFileToStretch)
    streched_audio = pyrubberband.time_stretch(y, sampleRate, speedFactor, rbargs={'--fine': '--fine'}) # Need to add rbarges in weird way because it demands a dictionary of two values
    soundfile.write(f'{workingFolder}\\temp_stretched.wav', streched_audio, sampleRate)
    #soundfile.write(f'{workingFolder}\\{num}_s.wav', streched_audio, sampleRate) # For debugging, saves the stretched audio files
    return AudioSegment.from_file(f'{workingFolder}\\temp_stretched.wav', format="wav"), subsDict

def build_audio(subsDict, totalAudioLength, highQualityMode=False):
    canvas = create_canvas(totalAudioLength)
    for key, value in subsDict.items():
        filePathMp3 = value['TTS_FilePath']
        filePathWav = workingFolder + "\\" + key + ".wav"

        # Trim the clip and re-write file
        rawClip = AudioSegment.from_file(filePathMp3, format="mp3", frame_rate=nativeSampleRate)
        trimmedClip = trim_clip(rawClip)
        trimmedClip.export(filePathWav, format="wav")

        # Stretch the clip to the desired duration
        stretchedClip, subsDict = stretch_audio(subsDict, filePathWav, value['duration_ms'], num=key)
        canvas = insert_audio(canvas, stretchedClip, value['start_ms'])

        # Print progress and overwrite line next time
        print(f" Processed Audio: {key} of {len(subsDict)}", end="\r")

    canvas.export("final.wav", format="wav")

    return subsDict
