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
OUTPUT_FOLDER = "output"

# Set working folder
WORKING_FOLDER = "workingFolder"

# Read config files
CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
BATCH_CONFIG = configparser.ConfigParser()
BATCH_CONFIG.read('batch.ini')
CLOUD_CONFIG = configparser.ConfigParser()
CLOUD_CONFIG.read('cloud_service_settings.ini')

# Get variables from configs
NATIVE_SAMPLE_RATE = int(CONFIG['SETTINGS']['synth_sample_rate'])
ORIGINAL_VIDEO_FILE = os.path.abspath(BATCH_CONFIG['SETTINGS']['original_video_file_path'].strip("\""))
SKIP_SYNTHESIZE = parse_bool(CONFIG['SETTINGS']['skip_synthesize'])
FORCE_STRETCH = parse_bool(CONFIG['SETTINGS']['force_stretch_with_twopass'])
OUTPUT_FORMAT = CONFIG['SETTINGS']['output_format'].lower()
BATCH_SYNTHESIZE = parse_bool(CLOUD_CONFIG['CLOUD']['batch_tts_synthesize'])
TTS_SERVICE = CLOUD_CONFIG['CLOUD']['tts_service']

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

def create_canvas(canvas_duration: int, frame_rate: int = NATIVE_SAMPLE_RATE ) -> AudioSegment:
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
    virtual_temp_audio_file = io.BytesIO()
    # Write the raw string to virtual temp audio file
    data, sample_rate = soundfile.read(audio_file_to_stretch)
    # Need to add rbarges in weird way because it demands a dictionary of two values
    stretched_audio = pyrubberband.time_stretch(y=data, sr=sample_rate, rate=speed_factor, rbargs={'--fine': '--fine'})
    # soundfile.write(f'{workingFolder}\\temp_stretched.wav', streched_audio, sampleRate)
    soundfile.write(virtual_temp_audio_file, stretched_audio, sample_rate, format='wav')
    # For debugging, saves the stretched audio files
    # soundfile.write(f'{workingFolder}\\{num}_s.wav', streched_audio, sampleRate)
    # return AudioSegment.from_file(f'{workingFolder}\\temp_stretched.wav', format="wav")
    return AudioSegment.from_file(virtual_temp_audio_file, format="wav")

def generate_virtual_audio_file(path: str, file_format: str = "mp3", frame_rate: int = NATIVE_SAMPLE_RATE) -> bytes:
    """Trims audio file and returns a virtual file

    Args:
        path (str): Path to audio file

    Returns:
        bytes: Virtual file 
    """
    clip: AudioSegment = trim_clip(AudioSegment.from_file(file=path, format=file_format, frame_rate=frame_rate))
    buffer: bytes = io.BytesIO()
    # Create virtual file with audio to be read later
    clip.export(buffer, format="wav")
    return buffer

def generate_filename(lang_dict: dict, original_video_file: str, output_folder: str) -> str:
    """Use video file name to use in the name of the output file. Add language name and language code

    Args:
        lang_dict (dict): dictionary containing language code and language name
        original_video_file (str): location of original video file
        output_folder (str): location of folder to save output file

    Raises:
        Exception: Invalid output format. Must be mp3, wav, or aac

    Returns:
        str: Absolute destination path for output file
    """
    if OUTPUT_FORMAT not in ["mp3", "wav", "aac"]:
        raise Exception("Invalid output format. Must be mp3, wav, or aac")
    
    lang = langcodes.get(lang_dict['languageCode'])
    lang_name = langcodes.get(lang_dict['languageCode']).get(lang.to_alpha3()).display_name()

    output_file = f"{pathlib.Path(original_video_file).stem} - {lang_name} - {lang_dict['languageCode']}.{OUTPUT_FORMAT}"
    
    return os.path.join(output_folder, output_file)

def synthesize(all_clips: dict, lang_dict: dict) -> dict:
    """Synthesize audio for all clips

    Args:
        all_clips (dict): All clips to synthesize
        lang_dict (dict): Dict containing language code and language name

    Returns:
        dict: Dict containing all clips with synthesized audio
    """
    if BATCH_SYNTHESIZE and TTS_SERVICE == 'azure':
        return TTS.synthesize_dictionary_batch(all_clips, lang_dict, skipSynthesize=SKIP_SYNTHESIZE, secondPass=True)
    else:
        return TTS.synthesize_dictionary(all_clips, lang_dict, skipSynthesize=SKIP_SYNTHESIZE, secondPass=True)

def build_audio(all_clips: dict, lang_dict: dict, total_length: int, use_two_pass: bool) -> AudioSegment:
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
    # item counter for keeping track of progress
    count: int = 0
    # Create canvas to overlay audio onto
    canvas: AudioSegment = create_canvas(total_length)
    for _, value in all_clips.items():
        value['TTS_FilePath_Trimmed'] = os.path.join(WORKING_FOLDER, f"{_}_t.wav")
        # First trim silence off the audio files
        clip: bytes = generate_virtual_audio_file(value['TTS_FilePath'])
        print(f"  Trimming Silence: {count} of {len(all_clips)}")
        # Calculate speed factors for each clip, aka how much to stretch the audio
        value['speed_factor'] = get_speed_factor(clip, value['duration_ms'])
        print(f"  Calculated Speed Factor: {count} of {len(all_clips)}")

        # If two pass voice synth is enabled, have API re-synthesize the clips at the new speed
        if use_two_pass:
            all_clips = synthesize(all_clips, lang_dict)
            # Trim the clip and re-write file
            clip = generate_virtual_audio_file(value['TTS_FilePath'])
            
            if FORCE_STRETCH:
                value['speed_factor'] = get_speed_factor(clip, value['duration_ms'])
                #stretchedClip = stretch_audio(value['TTS_FilePath_Trimmed'], speedFactor=subsDict[key]['speed_factor'])
                clip = stretch_audio(clip, value['speed_factor'])
                print(f"  Calculated Speed Factor (2nd Pass): {count} of {len(all_clips)}")
                #stretchedClip = AudioSegment.from_file(value['TTS_FilePath_Trimmed'], format="wav")
            else:
                clip = AudioSegment.from_file(clip, format="wav")

            print(f"  Trimmed Audio (2nd Pass): {count} of {len(all_clips)}")

        canvas = insert_audio(canvas, clip, value['start_ms'])
        print(f" Final Audio Insert: {count} of {len(all_clips)}")

    filename = generate_filename(lang_dict, ORIGINAL_VIDEO_FILE, OUTPUT_FOLDER)
    # Pydub doesn't accept "aac" as a format, so we have to use "mp4" instead.
    # Alternatively, could use "adts" with file extension "aac"
    file_format = OUTPUT_FORMAT if OUTPUT_FORMAT is not "aac" else "adts"
    canvas = canvas.set_channels(2) # Change from mono to stereo
    canvas.export(filename=filename, format=file_format, bitrate="192k")

    return canvas
