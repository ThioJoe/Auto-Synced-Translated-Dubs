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
import subprocess

# Set working folder
workingFolder = "workingFolder"

# If macOS, add current working directory to path for session for rubberband
if sysPlatform() == "Darwin":
    os.environ['PATH'] += os.pathsep + os.getcwd()

def trim_clip(inputSound: AudioSegment) -> AudioSegment:
    trim_leading_silence = lambda x: x[detect_leading_silence(x):]
    trim_trailing_silence = lambda x: trim_leading_silence(x.reverse()).reverse()
    strip_silence = lambda x: trim_trailing_silence(trim_leading_silence(x))
    
    return strip_silence(inputSound)

# Function to insert audio into canvas at specific point
def insert_audio(canvas, audioToOverlay, startTimeMs):
    # Create a copy of the canvas
    canvasCopy = canvas
    # Overlay the audio onto the copy
    canvasCopy = canvasCopy.overlay(audioToOverlay, position=int(startTimeMs))
    # Return the copy
    return canvasCopy

# Function to create a canvas of a specific duration in miliseconds
def create_canvas(canvasDuration, frame_rate=48000):
    canvas = AudioSegment.silent(duration=canvasDuration, frame_rate=frame_rate)
    return canvas

def get_speed_factor(subsDict, trimmedAudio, desiredDuration, num):
    virtualTempFile = AudioSegment.from_file(trimmedAudio, format="wav")
    rawDuration = virtualTempFile.duration_seconds
    trimmedAudio.seek(0) # This MUST be done to reset the file pointer to the start of the file, otherwise will get errors next time try to access the virtual files
    # Calculate the speed factor, put into dictionary
    desiredDuration = float(desiredDuration)
    speedFactor = (rawDuration*1000) / desiredDuration
    subsDict[num][SubsDictKeys.speed_factor] = speedFactor
    return subsDict

def stretch_with_rubberband(y, sampleRate, speedFactor):
    rubberband_streched_audio = pyrubberband.time_stretch(y, sampleRate, speedFactor, rbargs={'--fine': '--fine'}) # Need to add rbarges in weird way because it demands a dictionary of two values
    return rubberband_streched_audio

def stretch_with_ffmpeg(audioInput, speed_factor):
    min_speed_factor = 0.5
    max_speed_factor = 100.0
    filter_loop_count = 1

    # Validate speed_factor and calculate filter_loop_count
    if speed_factor < min_speed_factor:
        filter_loop_count = math.ceil(math.log(speed_factor) / math.log(min_speed_factor))
        speed_factor = speed_factor ** (1 / filter_loop_count)
        if speed_factor < 0.001:
            raise ValueError(f"ERROR: Speed factor is extremely low, and likely an error. It was: {speed_factor}")
    elif speed_factor > max_speed_factor:
        raise ValueError(f"ERROR: Speed factor cannot be over 100. It was {speed_factor}.")

    # Prepare ffmpeg command
    command = ['ffmpeg', '-i', 'pipe:0', '-filter:a', f'atempo={speed_factor}', '-f', 'wav', 'pipe:1']
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Pass the audio data to ffmpeg and read the processed data
    out, err = process.communicate(input=audioInput.getvalue())

    # Check for errors
    if process.returncode != 0:
        raise Exception(f'ffmpeg error: {err.decode()}')

    # Convert the output bytes to a NumPy array to be compatible with rest of the program
    # audio_data = numpy.frombuffer(out, numpy.int16)
    # Convert to float64 (which is the format used by pyrubberband)
    # audio_data = audio_data.astype(numpy.float64)
    # # Normalize the data to the range of float64 audio
    # audio_data /= numpy.iinfo(numpy.int16).max

    return out # Returns bytes

def stretch_audio_clip(audioFileToStretch, speedFactor, num):
    virtualTempAudioFile = io.BytesIO()
    # Write the raw string to virtualtempaudiofile
    audioObj, sampleRate = soundfile.read(audioFileToStretch) # auddioObj is a numpy array
    
    # Stretch the audio using user specified method
    if config.local_audio_stretch_method == 'ffmpeg':
        stretched_audio = stretch_with_ffmpeg(audioFileToStretch, speedFactor)
        virtualTempAudioFile.write(stretched_audio)
        if config.debug_mode:
            # For debugging, save the stretched audio file using soundfile
            debug_file_path = os.path.join(workingFolder, f'{num}_stretched_ffmpeg.wav')
            with open(debug_file_path, 'wb') as f:
                f.write(stretched_audio)
    elif config.local_audio_stretch_method == 'rubberband':
        stretched_audio = stretch_with_rubberband(audioObj, sampleRate, speedFactor)
        #soundfile.write(f'{workingFolder}\\temp_stretched.wav', streched_audio, sampleRate)
        soundfile.write(virtualTempAudioFile, stretched_audio, sampleRate, format='wav')
        if config.debug_mode:
            soundfile.write(os.path.join(workingFolder, f'{num}_stretched.wav'), stretched_audio, sampleRate) # For debugging, saves the stretched audio files
    #return AudioSegment.from_file(f'{workingFolder}\\temp_stretched.wav', format="wav")
    return AudioSegment.from_file(virtualTempAudioFile, format="wav")


def build_audio(subsDict, langDict, totalAudioLength, twoPassVoiceSynth=False):
    virtualTrimmedFileDict = {}
    # First trim silence off the audio files
    for key, value in subsDict.items():
        filePathTrimmed = os.path.join(workingFolder,  str(key)) + "_trimmed.wav"
        subsDict[key][SubsDictKeys.TTS_FilePath_Trimmed] = filePathTrimmed

        # Trim the clip and re-write file
        try:
            rawClip = AudioSegment.from_file(value[SubsDictKeys.TTS_FilePath], format="mp3")
        except KeyError:
            print("\nERROR: An expected file was not found. This is likely because the TTS service failed to synthesize the audio. Refer to any error messages above.")
            sys.exit()
        except FileNotFoundError:
            if value[SubsDictKeys.TTS_FilePath] == "Failed":
                print("\nProgram failed because some audio was not synthesized. Refer to any error messages above.")
            else:
                print("\nERROR: An expected file was not found. This is likely because the TTS service failed to synthesize the audio. Refer to any error messages above.")
            sys.exit()
        trimmedClip = trim_clip(rawClip)
        if config.debug_mode:
            trimmedClip.export(filePathTrimmed, format="wav")

        # Create virtual file in dictionary with audio to be read later
        tempTrimmedFile = io.BytesIO()
        trimmedClip.export(tempTrimmedFile, format="wav")
        virtualTrimmedFileDict[key] = tempTrimmedFile
        keyIndex = list(subsDict.keys()).index(key)
        print(f" Trimmed Audio: {keyIndex+1} of {len(subsDict)}", end="\r")
    print("\n")

    # Calculates speed factor if necessary. Azure doesn't need this, so skip it
    if not cloudConfig.tts_service == TTSService.AZURE or config.force_always_stretch == True:
        # Calculate speed factors for each clip, aka how much to stretch the audio
        for key, value in subsDict.items():
            #subsDict = get_speed_factor(subsDict, value[SubsDictKeys.TTS_FilePath_Trimmed], value[SubsDictKeys.duration_ms], num=key)
            subsDict = get_speed_factor(subsDict, virtualTrimmedFileDict[key], value[SubsDictKeys.duration_ms], num=key)
            keyIndex = list(subsDict.keys()).index(key)
            print(f" Calculated Speed Factor: {keyIndex+1} of {len(subsDict)}", end="\r")
        print("\n")
        
    # Decide if doing two pass voice synth
    servicesToUseTwoPass = [TTSService.GOOGLE]
    servicesSupportingExactDuration = [TTSService.AZURE]
    if cloudConfig.tts_service not in servicesToUseTwoPass:
        twoPassVoiceSynth = False
    if cloudConfig.tts_service in servicesSupportingExactDuration:
        twoPassVoiceSynth = False

    # If two pass voice synth is enabled, have API re-synthesize the clips at the new speed
    # Azure allows direct specification of audio duration, so no need to re-synthesize
    if twoPassVoiceSynth == True:
        if cloudConfig.batch_tts_synthesize == True and cloudConfig.tts_service == TTSService.AZURE:
            subsDict = TTS.synthesize_dictionary_batch(subsDict, langDict, skipSynthesize=config.skip_synthesize, secondPass=True)
        else:
            subsDict = TTS.synthesize_dictionary(subsDict, langDict, skipSynthesize=config.skip_synthesize, secondPass=True)
            
        for key, value in subsDict.items():
            # Trim the clip and re-write file
            rawClip = AudioSegment.from_file(value[SubsDictKeys.TTS_FilePath], format="mp3")
            trimmedClip = trim_clip(rawClip)
            if config.debug_mode:
                # Remove '.wav' from the end of the file path
                secondPassTrimmedFile = value[SubsDictKeys.TTS_FilePath_Trimmed][:-4] + "_p2_trimmed.wav"
                trimmedClip.export(secondPassTrimmedFile, format="wav")
            trimmedClip.export(virtualTrimmedFileDict[key], format="wav")
            keyIndex = list(subsDict.keys()).index(key)
            print(f" Trimmed Audio (2nd Pass): {keyIndex+1} of {len(subsDict)}", end="\r")
        print("\n")

        if config.force_stretch_with_twopass == True:
            for key, value in subsDict.items():
                subsDict = get_speed_factor(subsDict, virtualTrimmedFileDict[key], value[SubsDictKeys.duration_ms], num=key)
                keyIndex = list(subsDict.keys()).index(key)
                print(f" Calculated Speed Factor (2nd Pass): {keyIndex+1} of {len(subsDict)}", end="\r")
            print("\n")

    # Create canvas to overlay audio onto
    canvas = create_canvas(totalAudioLength)

    # Stretch audio and insert into canvas
    for key, value in subsDict.items():
        if ((not twoPassVoiceSynth or config.force_stretch_with_twopass == True) and (cloudConfig.tts_service not in servicesSupportingExactDuration)) or config.force_always_stretch == True: # Don't stretch if azure is used unless forced
            #stretchedClip = stretch_audio_clip(value[SubsDictKeys.TTS_FilePath_Trimmed], speedFactor=subsDict[key][SubsDictKeys.speed_factor], num=key)
            stretchedClip = stretch_audio_clip(virtualTrimmedFileDict[key], speedFactor=subsDict[key][SubsDictKeys.speed_factor], num=key)
        else:
            #stretchedClip = AudioSegment.from_file(value[SubsDictKeys.TTS_FilePath_Trimmed], format="wav")
            stretchedClip = AudioSegment.from_file(virtualTrimmedFileDict[key], format="wav")
            virtualTrimmedFileDict[key].seek(0) # Not 100% sure if this is necessary but it was in the other place it is used

        canvas = insert_audio(canvas, stretchedClip, value[SubsDictKeys.start_ms])
        
        # Print warning if audio clip is longer than expected and would overlap next clip
        currentClipExpectedDuration = int(value[SubsDictKeys.duration_ms])
        currentClipTrueDuration = stretchedClip.duration_seconds * 1000
        difference = str(round(currentClipTrueDuration - currentClipExpectedDuration))
        if key < len(subsDict) and (currentClipTrueDuration + int(value[SubsDictKeys.start_ms]) > int(subsDict[key+1][SubsDictKeys.start_ms])):
            print(f"WARNING: Audio clip {str(key)} for language {langDict[LangDictKeys.languageCode]} is {difference}ms longer than expected and may overlap the next clip. Inspect the audio file after completion.")
        elif key == len(subsDict) and (currentClipTrueDuration + int(value[SubsDictKeys.start_ms]) > totalAudioLength):
            print(f"WARNING: Audio clip {str(key)} for language {langDict[LangDictKeys.languageCode]} is {difference}ms longer than expected and may cut off at the end of the file. Inspect the audio file after completion.")
            
            
        keyIndex = list(subsDict.keys()).index(key)
        print(f" Final Audio Processed: {keyIndex+1} of {len(subsDict)}", end="\r")
    print("\n")

    # Use video file name to use in the name of the output file. Add language name and language code
    lang = langcodes.get(langDict[LangDictKeys.languageCode])
    langName = langcodes.get(langDict[LangDictKeys.languageCode]).get(lang.to_alpha3()).display_name()
    if config.debug_mode and not os.path.isfile(ORIGINAL_VIDEO_PATH):
        outputFileName = "debug" + f" - {langName} - {langDict[LangDictKeys.languageCode]}."
    else:
        outputFileName = pathlib.Path(ORIGINAL_VIDEO_PATH).stem + f" - {langName} - {langDict[LangDictKeys.languageCode]}."
    # Set output path
    outputFileName = os.path.join(OUTPUT_FOLDER, outputFileName)

    # Determine string to use for output format and file extension based on config setting  
    if config.output_format == AudioFormat.AAC: # Pydub doesn't accept "aac" as a format, so we have to use "mp4" instead. Alternatively, could use "adts" with file extension "aac"
        outputFileName += "aac"
        formatString = "adts"
    else:
        outputFileName += config.output_format
        formatString = config.output_format

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
