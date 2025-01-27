#!/usr/bin/env python
# coding: utf-8

# Based on Microsoft Azure sample code found here: https://github.com/Azure-Samples/cognitive-services-speech-sdk/blob/master/samples/batch-synthesis/python/synthesis.py
# Original License Info Below:
# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE.md file in the project root for full license information.
#--------------------------------------------------------------------------------------------------------
import json
import logging
import sys
import uuid
from typing import Optional

import requests
import configparser

from Scripts.shared_imports import *

logging.basicConfig(stream=sys.stdout, level=logging.ERROR,
        format="[%(asctime)s] %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p %Z")
logger = logging.getLogger(__name__)

# Your Speech resource key and region
# This example requires environment variables named "SPEECH_KEY" and "SPEECH_REGION"

AZURE_SPEECH_KEY = cloudConfig.azure_speech_key
AZURE_SPEECH_REGION = cloudConfig.azure_speech_region
API_VERSION = "2024-04-01"

NAME = "Simple synthesis"
DESCRIPTION = "Simple synthesis description"

# The service host suffix.
SERVICE_HOST = "api.cognitive.microsoft.com"

def _create_job_id():
    # the job ID must be unique in current speech resource
    # you can use a GUID or a self-increasing number
    return uuid.uuid4()

def submit_synthesis(payload) -> Optional[str]:
    newJobID = _create_job_id()
    
    url = f'https://{AZURE_SPEECH_REGION}.{SERVICE_HOST}/texttospeech/batchsyntheses/{newJobID}?api-version={API_VERSION}'
    header = {
        'Ocp-Apim-Subscription-Key': AZURE_SPEECH_KEY,
        'Content-Type': 'application/json'
    }

    response = requests.put(url, json.dumps(payload), headers=header)
    if response.status_code < 400:
        logger.info('Batch synthesis job submitted successfully')
        logger.info(f'Job ID: {response.json()["id"]}')
        return response.json()["id"]
    else:
        logger.error(f'Failed to submit batch synthesis job: {response.text}')
        return None


def get_synthesis(job_id) -> Optional[requests.Response]:
    url = f'https://{AZURE_SPEECH_REGION}.{SERVICE_HOST}/texttospeech/batchsyntheses/{job_id}?api-version={API_VERSION}'
    header = {
        'Ocp-Apim-Subscription-Key': AZURE_SPEECH_KEY
    }
    response:requests.Response = requests.get(url, headers=header)
    if response.status_code < 400:
        logger.info('Get batch synthesis job successfully')
        logger.info(response.json())
        #return response.json()['status']
        return response
    else:
        logger.error(f'Failed to get batch synthesis job: {response.text}')
        return None

def list_synthesis_jobs(skip: int = 0, top: int = 100) -> None:
    """List all batch synthesis jobs in the subscription"""
    url = f'https://{AZURE_SPEECH_REGION}.{SERVICE_HOST}/texttospeech/batchsyntheses?skip={skip}&top={top}?api-version={API_VERSION}'
    header = {
        'Ocp-Apim-Subscription-Key': AZURE_SPEECH_KEY
    }
    response = requests.get(url, headers=header)
    if response.status_code < 400:
        logger.info(f'List batch synthesis jobs successfully, got {len(response.json()["values"])} jobs')
        logger.info(response.json())
    else:
        logger.error(f'Failed to list batch synthesis jobs: {response.text}')

