from dataclasses import dataclass
from typing import Union, Literal
import configparser

from Scripts.enums import *

def parse_bool_strict(input: str) -> bool:
    if input.lower() == 'true':
        return True
    elif input.lower() == 'false':
        return False
    else:
        raise ValueError(f'Invalid value "{input}". Must be "True" or "False"')
    
def parse_int_str_union(input: str, possibleStringsList: list[str]) -> Union[str, int]:
    try:
        return int(input)
    except ValueError:
        # If it matches one of the possible strings, return the string it matches
        for possibleString in possibleStringsList:
            if input.lower() == possibleString.lower():
                return possibleString
        else:
            raise ValueError(f'Invalid value "{input}". Must be one of: {possibleStringsList}')

@dataclass
class CloudConfig:
    tts_service: TTSService
    translate_service: TranslateService
    use_fallback_google_translate: bool
    batch_tts_synthesize: bool
    google_project_id: str
    deepl_api_key: str
    azure_speech_key: str
    azure_speech_region: str
    elevenlabs_api_key: str
    elevenlabs_default_model: ElevenLabsModel
    elevenlabs_max_concurrent: int

    @classmethod
    def from_dict(cls, config_dict: dict) -> 'CloudConfig':
        return cls(
            tts_service=TTSService(config_dict['tts_service']),
            translate_service=TranslateService(config_dict['translate_service']),
            use_fallback_google_translate=parse_bool_strict(config_dict['use_fallback_google_translate']),
            batch_tts_synthesize=parse_bool_strict(config_dict['batch_tts_synthesize']),
            google_project_id=config_dict['google_project_id'],
            deepl_api_key=config_dict['deepl_api_key'],
            azure_speech_key=config_dict['azure_speech_key'],
            azure_speech_region=config_dict['azure_speech_region'],
            elevenlabs_api_key=config_dict['elevenlabs_api_key'],
            elevenlabs_default_model=ElevenLabsModel(config_dict['elevenlabs_default_model']),
            elevenlabs_max_concurrent=int(config_dict['elevenlabs_max_concurrent'])
        )

@dataclass
class Config:
    skip_translation: bool
    skip_synthesize: bool
    stop_after_translation: bool
    original_language: str
    formality_preference: FormalityPreference
    output_format: AudioFormat
    synth_audio_encoding: str
    synth_sample_rate: int
    two_pass_voice_synth: bool
    local_audio_stretch_method: AudioStretchMethod
    force_stretch_with_twopass: bool
    force_always_stretch: bool
    azure_sentence_pause: Union[str, int] # 'default' or int
    azure_comma_pause: Union[str, int] # 'default' or int
    add_line_buffer_milliseconds: int
    combine_subtitles_max_chars: int
    increase_max_chars_for_extreme_speeds: bool
    subtitle_gap_threshold_milliseconds: int
    prioritize_avoiding_fragmented_speech: bool
    speech_rate_goal: Union[str, int] # 'Auto' or int
    debug_mode: bool
    youtube_autosync_languages: list[str]

    @classmethod
    def from_dict(cls, config_dict: dict) -> 'Config':
        # Handle the youtube_autosync_languages list
        if isinstance(config_dict['youtube_autosync_languages'], str):
            languages = [lang.strip() for lang in config_dict['youtube_autosync_languages'].split(',')]
        else:
            languages = config_dict['youtube_autosync_languages']

        return cls(
            skip_translation=parse_bool_strict(config_dict['skip_translation']),
            skip_synthesize=parse_bool_strict(config_dict['skip_synthesize']),
            stop_after_translation=parse_bool_strict(config_dict['stop_after_translation']),
            original_language=config_dict['original_language'],
            formality_preference=FormalityPreference(config_dict['formality_preference']),
            output_format=AudioFormat(config_dict['output_format']),
            synth_audio_encoding=config_dict['synth_audio_encoding'],
            synth_sample_rate=int(config_dict['synth_sample_rate']),
            two_pass_voice_synth=parse_bool_strict(config_dict['two_pass_voice_synth']),
            local_audio_stretch_method=AudioStretchMethod(config_dict['local_audio_stretch_method']),
            force_stretch_with_twopass=parse_bool_strict(config_dict['force_stretch_with_twopass']),
            force_always_stretch=parse_bool_strict(config_dict['force_always_stretch']),
            azure_sentence_pause=parse_int_str_union(config_dict['azure_sentence_pause'], ["default"]),
            azure_comma_pause=parse_int_str_union(config_dict['azure_comma_pause'], ["default"]),
            add_line_buffer_milliseconds=int(config_dict['add_line_buffer_milliseconds']),
            combine_subtitles_max_chars=int(config_dict['combine_subtitles_max_chars']),
            increase_max_chars_for_extreme_speeds=parse_bool_strict(config_dict['increase_max_chars_for_extreme_speeds']),
            subtitle_gap_threshold_milliseconds=int(config_dict['subtitle_gap_threshold_milliseconds']),
            prioritize_avoiding_fragmented_speech=parse_bool_strict(config_dict['prioritize_avoiding_fragmented_speech']),
            speech_rate_goal=parse_int_str_union(config_dict['speech_rate_goal'], ["Auto"]),
            debug_mode=parse_bool_strict(config_dict['debug_mode']),
            youtube_autosync_languages=languages
        )
        
# ----------------------------------------------------------------



# Get Config Values
configRaw = configparser.ConfigParser()
configRaw.read('config.ini')
configRawDict = dict(configRaw['SETTINGS'])

cloudConfigRaw = configparser.ConfigParser()
cloudConfigRaw.read('cloud_service_settings.ini')
cloudConfigRawDict = dict(cloudConfigRaw['CLOUD'])

batchConfig = configparser.ConfigParser()
batchConfig.read('batch.ini') # Don't process this one, need sections in tact for languages
        
config = Config.from_dict(configRawDict)
cloudConfig = CloudConfig.from_dict(cloudConfigRawDict)
