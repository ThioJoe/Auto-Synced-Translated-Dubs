import soundfile
import pyrubberband
import configparser
import pathlib
import os
import io
import math
from platform import system as sysPlatform

from Scripts.shared_imports import *
import Scripts.TTS as TTS

from pydub import AudioSegment
from pydub.silence import detect_leading_silence
import langcodes
import numpy
import ffmpeg

# Set working folder
workingFolder = "workingFolder"

# If macOS, add current working directory to path for session for rubberband
if sysPlatform() == "Darwin":
    os.environ['PATH'] += os.pathsep + os.getcwd()


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
def create_canvas(canvasDuration, frame_rate=int(config['synth_sample_rate'])):
    canvas = AudioSegment.silent(duration=canvasDuration, frame_rate=frame_rate)
    return canvas

def get_speed_factor(subsDict, trimmedAudio, desiredDuration, num):
    virtualTempFile = AudioSegment.from_file(trimmedAudio, format="wav")
    rawDuration = virtualTempFile.duration_seconds
    trimmedAudio.seek(0) # This MUST be done to reset the file pointer to the start of the file, otherwise will get errors next time try to access the virtual files
    # Calculate the speed factor, put into dictionary
    desiredDuration = float(desiredDuration)
    speedFactor = (rawDuration*1000) / desiredDuration
    subsDict[num]['speed_factor'] = speedFactor
    return subsDict

def stretch_with_rubberband(y, sampleRate, speedFactor):
    rubberband_streched_audio = pyrubberband.time_stretch(y, sampleRate, speedFactor, rbargs={'--fine': '--fine'}) # Need to add rbarges in weird way because it demands a dictionary of two values
    return rubberband_streched_audio

def stretch_with_ffmpeg(audio, speed_factor):
    min_speed_factor = 0.5
    max_speed_factor = 100.0
    filter_loop_count = 1
    # Initialize the input stream
    stream = ffmpeg.input(audio)
    
    if speed_factor < 0.5:
        # If between 0.25 and 0.5, can do 2 steps with each run's speed factor of square root the speed factor, between 0.125 and 0.25 cube root and so on.
        # Uses logarithms to calculate the number of steps and speed factor of each step
        filter_loop_count = math.ceil(math.log(speed_factor) / math.log(min_speed_factor))
        speed_factor = speed_factor ** (1 / filter_loop_count)
        # Catch if speed factor is ridiculously low, likely an error
        if speed_factor < 0.001:
            raise ValueError(f"ERROR: Speed factor is extremely low, and likely an error. It was: {speed_factor}")
    elif speed_factor > max_speed_factor:
        # If speed factor over 100 just throw an error, because that's crazy
        raise ValueError(f"ERROR: Speed factor cannot be over 100. It was {speed_factor}.")
    
    # Run the filter loop as many times as needed
    for i in range(filter_loop_count):
        # Apply the filter
        stream = ffmpeg.filter(stream, 'atempo', speed_factor)
    
    # Define the output stream with format
    stream = ffmpeg.output(stream, 'pipe:', format='wav')
    # Run the ffmpeg process and capture output
    out, _ = ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
    
    # Convert the output bytes to a NumPy array to be compatible with rest of program
    audio_data = numpy.frombuffer(out, numpy.int16)
    # Convert to float64 (which is the format used by pyrubberband)
    audio_data = audio_data.astype(numpy.float64)
    # Normalize the data to the range of float64 audio
    audio_data /= numpy.iinfo(numpy.int16).max
    
    return audio_data

def stretch_audio(audioFileToStretch, speedFactor, num):
    virtualTempAudioFile = io.BytesIO()
    # Write the raw string to virtualtempaudiofile
    audioObj, sampleRate = soundfile.read(audioFileToStretch)
    
    # Stretch the audio using user specified method
    if config['local_audio_stretch_method'] == 'ffmpeg':
        stretched_audio = stretch_with_ffmpeg(audioFileToStretch, speedFactor)
    elif config['local_audio_stretch_method'] == 'rubberband':
        stretched_audio = stretch_with_rubberband(audioObj, sampleRate, speedFactor)
    
    #soundfile.write(f'{workingFolder}\\temp_stretched.wav', streched_audio, sampleRate)
    soundfile.write(virtualTempAudioFile, stretched_audio, sampleRate, format='wav')
    if config['debug_mode']:
        soundfile.write(os.path.join(workingFolder, f'{num}_s.wav'), stretched_audio, sampleRate) # For debugging, saves the stretched audio files
    #return AudioSegment.from_file(f'{workingFolder}\\temp_stretched.wav', format="wav")
    return AudioSegment.from_file(virtualTempAudioFile, format="wav")


def build_audio(subsDict, langDict, totalAudioLength, twoPassVoiceSynth=False):
    if cloudConfig['tts_service'] == 'azure':
        twoPassVoiceSynth = False # Azure doesn't need two pass voice synth, so disable it

    virtualTrimmedFileDict = {}
    # First trim silence off the audio files
    for key, value in subsDict.items():
        filePathTrimmed = os.path.join(workingFolder,  str(key)) + "_t.wav"
        subsDict[key]['TTS_FilePath_Trimmed'] = filePathTrimmed

        # Trim the clip and re-write file
        rawClip = AudioSegment.from_file(value['TTS_FilePath'], format="mp3", frame_rate=int(config['synth_sample_rate']))
        trimmedClip = trim_clip(rawClip)
        if config['debug_mode']:
            trimmedClip.export(filePathTrimmed, format="wav")

        # Create virtual file in dictionary with audio to be read later
        tempTrimmedFile = io.BytesIO()
        trimmedClip.export(tempTrimmedFile, format="wav")
        virtualTrimmedFileDict[key] = tempTrimmedFile
        keyIndex = list(subsDict.keys()).index(key)
        print(f" Trimmed Audio: {keyIndex+1} of {len(subsDict)}", end="\r")
    print("\n")

    # Calculates speed factor if necessary. Azure doesn't need this, so skip it
    if not cloudConfig['tts_service'] == 'azure':
        # Calculate speed factors for each clip, aka how much to stretch the audio
        for key, value in subsDict.items():
            #subsDict = get_speed_factor(subsDict, value['TTS_FilePath_Trimmed'], value['duration_ms'], num=key)
            subsDict = get_speed_factor(subsDict, virtualTrimmedFileDict[key], value['duration_ms'], num=key)
            keyIndex = list(subsDict.keys()).index(key)
            print(f" Calculated Speed Factor: {keyIndex+1} of {len(subsDict)}", end="\r")
        print("\n")

    # If two pass voice synth is enabled, have API re-synthesize the clips at the new speed
    # Azure allows direct specification of audio duration, so no need to re-synthesize
    if twoPassVoiceSynth == True and not cloudConfig['tts_service'] == 'azure':
        if cloudConfig['batch_tts_synthesize'] == True and cloudConfig['tts_service'] == 'azure':
            subsDict = TTS.synthesize_dictionary_batch(subsDict, langDict, skipSynthesize=config['skip_synthesize'], secondPass=True)
        else:
            subsDict = TTS.synthesize_dictionary(subsDict, langDict, skipSynthesize=config['skip_synthesize'], secondPass=True)
            
        for key, value in subsDict.items():
            # Trim the clip and re-write file
            rawClip = AudioSegment.from_file(value['TTS_FilePath'], format="mp3", frame_rate=int(config['synth_sample_rate']))
            trimmedClip = trim_clip(rawClip)
            if config['debug_mode']:
                # Remove '.wav' from the end of the file path
                secondPassTrimmedFile = value['TTS_FilePath_Trimmed'][:-4] + "_p2_t.wav"
                trimmedClip.export(secondPassTrimmedFile, format="wav")
            trimmedClip.export(virtualTrimmedFileDict[key], format="wav")
            keyIndex = list(subsDict.keys()).index(key)
            print(f" Trimmed Audio (2nd Pass): {keyIndex+1} of {len(subsDict)}", end="\r")
        print("\n")

        if config['force_stretch_with_twopass'] == True:
            for key, value in subsDict.items():
                subsDict = get_speed_factor(subsDict, virtualTrimmedFileDict[key], value['duration_ms'], num=key)
                keyIndex = list(subsDict.keys()).index(key)
                print(f" Calculated Speed Factor (2nd Pass): {keyIndex+1} of {len(subsDict)}", end="\r")
            print("\n")

    # Create canvas to overlay audio onto
    canvas = create_canvas(totalAudioLength)

    # Stretch audio and insert into canvas
    for key, value in subsDict.items():
        if (not twoPassVoiceSynth or config['force_stretch_with_twopass'] == True) and not cloudConfig['tts_service'] == 'azure': # Don't stretch if azure is used
            #stretchedClip = stretch_audio(value['TTS_FilePath_Trimmed'], speedFactor=subsDict[key]['speed_factor'], num=key)
            stretchedClip = stretch_audio(virtualTrimmedFileDict[key], speedFactor=subsDict[key]['speed_factor'], num=key)
        else:
            #stretchedClip = AudioSegment.from_file(value['TTS_FilePath_Trimmed'], format="wav")
            stretchedClip = AudioSegment.from_file(virtualTrimmedFileDict[key], format="wav")
            virtualTrimmedFileDict[key].seek(0) # Not 100% sure if this is necessary but it was in the other place it is used

        canvas = insert_audio(canvas, stretchedClip, value['start_ms'])
        keyIndex = list(subsDict.keys()).index(key)
        print(f" Final Audio Processed: {keyIndex+1} of {len(subsDict)}", end="\r")
    print("\n")

    # Use video file name to use in the name of the output file. Add language name and language code
    lang = langcodes.get(langDict['languageCode'])
    langName = langcodes.get(langDict['languageCode']).get(lang.to_alpha3()).display_name()
    if config['debug_mode'] and not os.path.isfile(ORIGINAL_VIDEO_PATH):
        outputFileName = "debug" + f" - {langName} - {langDict['languageCode']}."
    else:
        outputFileName = pathlib.Path(ORIGINAL_VIDEO_PATH).stem + f" - {langName} - {langDict['languageCode']}."
    # Set output path
    outputFileName = os.path.join(OUTPUT_FOLDER, outputFileName)

    # Determine string to use for output format and file extension based on config setting
    outputFormat=config['output_format'].lower()
    if outputFormat == "mp3":
        outputFileName += "mp3"
        formatString = "mp3"
    elif outputFormat == "wav":
        outputFileName += "wav"
        formatString = "wav"
    elif outputFormat == "aac":
        #outputFileName += "m4a"
        #formatString = "mp4" # Pydub doesn't accept "aac" as a format, so we have to use "mp4" instead. Alternatively, could use "adts" with file extension "aac"
        outputFileName += "aac"
        formatString = "adts" # Pydub doesn't accept "aac" as a format, so we have to use "mp4" instead. Alternatively, could use "adts" with file extension "aac"

    canvas = canvas.set_channels(2) # Change from mono to stereo
    try:
        print("\nExporting audio file...")
        canvas.export(outputFileName, format=formatString, bitrate="192k")
    except:
        outputFileName = outputFileName + ".bak"
        canvas.export(outputFileName, format=formatString, bitrate="192k")
        print("\nThere was an issue exporting the audio, it might be a permission error. The file was saved as a backup with the extension .bak")
        print("Try removing the .bak extension then listen to the file to see if it worked.\n")
        input("Press Enter to exit...")

    return subsDict
