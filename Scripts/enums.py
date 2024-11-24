#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from enum import Enum

class TranslateService(Enum):
    GOOGLE = "google"
    DEEPL = "deepl"
    
    def __str__(self):
        return self.value

