#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from enum import Enum

class TranslateService(str, Enum):
    GOOGLE = "google"
    DEEPL = "deepl"

    def __str__(self):
        return self.value

class TTSService(str, Enum):
    AZURE = "azure"
    GOOGLE = "google"
    ELEVENLABS = "elevenlabs"
    
    def __str__(self):
        return self.value

class AudioFormat(str, Enum):
    MP3 = "mp3"
    AAC = "aac"
    WAV = "wav"
    
    def __str__(self):
        return self.value

class AudioStretchMethod(str, Enum):
    FFMPEG = "ffmpeg"
    RUBBERBAND = "rubberband"
    
    def __str__(self):
        return self.value

class ElevenLabsModel(str, Enum):
    MONOLINGUAL_V1 = "eleven_monolingual_v1"
    MULTILINGUAL_V2 = "eleven_multilingual_v2"
    DEFAULT = "default"
    
    def __str__(self):
        return self.value

class FormalityPreference(str, Enum):
    DEFAULT = "default"
    MORE = "more"
    LESS = "less"
    
    def __str__(self):
        return self.value
    
class LangDataKeys(str, Enum):
    translation_target_language = "translation_target_language"
    synth_voice_name = "synth_voice_name"
    synth_language_code = "synth_language_code"
    synth_voice_gender = "synth_voice_gender"
    translate_service = "translate_service"
    formality = "formality"
    synth_voice_model = "synth_voice_model"
    synth_voice_style = "synth_voice_style"
    
    def __str__(self):
        return self.value
    
class LangDictKeys(str, Enum):
    targetLanguage = "targetLanguage"
    voiceName = "voiceName"
    languageCode = "languageCode"
    voiceGender = "voiceGender"
    translateService = "translateService"
    formality = "formality"
    voiceModel = "voiceModel"
    voiceStyle = "voiceStyle"
    
    def __str__(self):
        return self.value
    
class SubsDictKeys(str, Enum):
    start_ms = "start_ms"
    end_ms = "end_ms"
    duration_ms = "duration_ms"
    text = "text"
    break_until_next = "break_until_next"
    srt_timestamps_line = "srt_timestamps_line"
    start_ms_buffered = "start_ms_buffered"
    end_ms_buffered = "end_ms_buffered"
    duration_ms_buffered = "duration_ms_buffered"
    translated_text = "translated_text"
    originalIndex = "originalIndex"
    char_rate = "char_rate"
    char_rate_diff = "char_rate_diff"
    TTS_FilePath = "TTS_FilePath"
    TTS_FilePath_Trimmed = "TTS_FilePath_Trimmed"
    speed_factor = "speed_factor"

    def __str__(self):
        return self.value
    
class VariousDefaults():
    defaultSpeechRateGoal:float = 20

