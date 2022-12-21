from typing import Any
import configparser
import pathlib
import os
import io
import soundfile
import pyrubberband
import langcodes
from pydub.silence import detect_leading_silence
from pydub import AudioSegment
import TTS
from utils import parse_bool

# TODO: MOVE THIS INTO A VARIABLE AT SOME POINT
output_folder = "output"

# Set working folder
working_folder = "workingFolder"

# Read config files
config = configparser.ConfigParser()
config.read('config.ini')
batch_config = configparser.ConfigParser()
batch_config.read('batch.ini')
cloud_config = configparser.ConfigParser()
cloud_config.read('cloud_service_settings.ini')

# Get variables from configs
native_sample_rate = int(config['SETTINGS']['synth_sample_rate'])
original_video_file = os.path.abspath(batch_config['SETTINGS']['original_video_file_path'].strip("\""))
skip_synthesize = parse_bool(config['SETTINGS']['skip_synthesize'])
force_two_pass_stretch = parse_bool(config['SETTINGS']['force_stretch_with_twopass'])
output_format = config['SETTINGS']['output_format'].lower()
batch_synthesize = parse_bool(cloud_config['CLOUD']['batch_tts_synthesize'])
tts_service = cloud_config['CLOUD']['tts_service']

def trim_clip(input_sound: AudioSegment) -> AudioSegment:
    """Trims leading and trailing silence from audio clip

    Args:
        input_sound (AudioSegment): Input audio clip

    Returns:
        AudioSegment: Input audio clip with leading and trailing silence removed
    """
    trim_leading_silence: AudioSegment = lambda x: x[detect_leading_silence(x) :]
    trim_trailing_silence: AudioSegment = lambda x: trim_leading_silence(x.reverse()).reverse()
    strip_silence: AudioSegment = lambda x: trim_trailing_silence(trim_leading_silence(x))
    return strip_silence(input_sound)

def insert_audio(canvas: AudioSegment, audio_to_overlay: AudioSegment, start_time_ms: int) -> AudioSegment:
    """Function to insert audio into canvas at specific point

    Args:
        canvas (AudioSegment): Base audio to insert into
        audio_to_overlay (AudioSegment): Audio to insert into canvas
        start_time_ms (int): Point in milliseconds to insert audio

    Returns:
        AudioSegment: Base with inserted audio
    """
    return canvas.overlay(audio_to_overlay, position=int(start_time_ms))

def create_canvas(canvas_duration: int, frame_rate: int = native_sample_rate ) -> AudioSegment:
    """Function to create a canvas of a specific duration in milliseconds

    Args:
        canvas_duration (int): Length of canvas in milliseconds
        frame_rate (int, optional): Sample rate for canvas. Defaults to native_sample_rate.

    Returns:
        AudioSegment: Canvas of specified duration
    """
    return AudioSegment.silent(duration=canvas_duration, frame_rate=frame_rate)

def get_speed_factor(audio: AudioSegment, desired_duration: float) -> float:
    """Function to calculate the speed factor for stretching audio

    Args:
        trimmed_audio (AudioSegment): Audio to calculate speed factor for
        desired_duration (float): Desired duration of audio in milliseconds

    Returns:
        float: Multiplication speed factor
    """
    raw_duration: AudioSegment = AudioSegment.from_file(audio, format="wav").duration_seconds
    # This MUST be done to reset the file pointer to the start of the file, otherwise will get errors
    # next time try to access the virtual files
    audio.seek(0)
    # Calculate the speed factor, put into dictionary
    return (raw_duration*1000) / float(desired_duration)

def stretch_audio(audio_file_to_stretch: Any, speed_factor: float,) -> AudioSegment:
    """Function to stretch audio to a specific duration

    Args:
        audio_file_to_stretch (Any): Audio file to stretch
        speed_factor (float): Factor to stretch audio by

    Returns:
        AudioSegment: Stretched audio
    """

    """Function to build the final audio file

    Args:
        subs_dict (_type_): _description_
        langDict (_type_): _description_
        totalAudioLength (_type_): _description_
        use_two_pass (bool): _description_

    Raises:
        Exception: _description_

    Returns:
        _type_: _description_
    """
    # First trim silence off the audio files
    for key, value in subsDict.items():
        filePathTrimmed = workingFolder + "\\" + key + "_t.wav"
        subsDict[key]['TTS_FilePath_Trimmed'] = filePathTrimmed

        # Trim the clip and re-write file
        rawClip = AudioSegment.from_file(value['TTS_FilePath'], format="mp3", frame_rate=nativeSampleRate)
        trimmedClip = trim_clip(rawClip)
        #trimmedClip.export(filePathTrimmed, format="wav")

        # Create virtual file in dictionary with audio to be read later
        tempTrimmedFile = io.BytesIO()
        trimmedClip.export(tempTrimmedFile, format="wav")
        virtualTrimmedFileDict[key] = tempTrimmedFile
        keyIndex = list(subsDict.keys()).index(key)
        print(f" Trimmed Audio: {keyIndex+1} of {len(subsDict)}", end="\r")
    print("\n")

    # Calculate speed factors for each clip, aka how much to stretch the audio
    for key, value in subsDict.items():
        #subsDict = get_speed_factor(subsDict, value['TTS_FilePath_Trimmed'], value['duration_ms'], num=key)
        subsDict = get_speed_factor(subsDict, virtualTrimmedFileDict[key], value['duration_ms'], num=key)
        keyIndex = list(subsDict.keys()).index(key)
        print(f" Calculated Speed Factor: {keyIndex+1} of {len(subsDict)}", end="\r")
    print("\n")

    # If two pass voice synth is enabled, have API re-synthesize the clips at the new speed
    if twoPassVoiceSynth == True:
        if batchSynthesize == True and tts_service == 'azure':
            subsDict = TTS.synthesize_dictionary_batch(subsDict, langDict, skipSynthesize=skipSynthesize, secondPass=True)
        else:
            subsDict = TTS.synthesize_dictionary(subsDict, langDict, skipSynthesize=skipSynthesize, secondPass=True)
            
        for key, value in subsDict.items():
            # Trim the clip and re-write file
            rawClip = AudioSegment.from_file(value['TTS_FilePath'], format="mp3", frame_rate=nativeSampleRate)
            trimmedClip = trim_clip(rawClip)
            #trimmedClip.export(value['TTS_FilePath_Trimmed'], format="wav")
            trimmedClip.export(virtualTrimmedFileDict[key], format="wav")
            keyIndex = list(subsDict.keys()).index(key)
            print(f" Trimmed Audio (2nd Pass): {keyIndex+1} of {len(subsDict)}", end="\r")
        print("\n")

        if forceTwoPassStretch == True:
            for key, value in subsDict.items():
                subsDict = get_speed_factor(subsDict, virtualTrimmedFileDict[key], value['duration_ms'], num=key)
                keyIndex = list(subsDict.keys()).index(key)
                print(f" Calculated Speed Factor (2nd Pass): {keyIndex+1} of {len(subsDict)}", end="\r")
            print("\n")

    # Create canvas to overlay audio onto
    canvas = create_canvas(totalAudioLength)

    # Stretch audio and insert into canvas
    for key, value in subsDict.items():
        if not twoPassVoiceSynth or forceTwoPassStretch == True:
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
    outputFileName = pathlib.Path(originalVideoFile).stem + f" - {langName} - {langDict['languageCode']}."
    # Set output path
    outputFileName = os.path.join(outputFolder, outputFileName)

    # Determine string to use for output format and file extension based on config setting
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
    canvas.export(outputFileName, format=formatString, bitrate="192k")

    return subsDict
