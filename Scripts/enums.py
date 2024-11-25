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