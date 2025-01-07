import boto3
import json
import os
from typing import List, Dict, Any, Optional
from botocore.exceptions import BotoCoreError, ClientError

# Initialize the Polly client with a specific region
polly_client = boto3.client('polly', region_name='us-west-2')

def load_input_data(file_path: str) -> List[Dict[str, Any]]:
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        return []
    except json.JSONDecodeError:
        print(f"Error: The file {file_path} contains invalid JSON.")
        return []

def get_compatible_voices(language_code: str) -> List[str]:
    try:
        response = polly_client.describe_voices(LanguageCode=language_code)
        return [voice['Id'] for voice in response['Voices'] if 'SupportedEngines' in voice and 'standard' in voice['SupportedEngines']]
    except (BotoCoreError, ClientError) as error:
        print(f"Error getting voices: {error}")
        return []

def generate_audio(text: str, voice_id: str, lang_code: str, polly_client=None) -> Optional[bytes]:
    try:
        if polly_client is None:
            polly_client = boto3.client('polly', region_name='us-west-2')
            
        response = polly_client.synthesize_speech(
            Text=text,
            OutputFormat='mp3',
            VoiceId=voice_id,
            LanguageCode=lang_code
        )
        return response['AudioStream'].read()
    except (BotoCoreError, ClientError) as error:
        print(f"Error generating audio for voice {voice_id}: {error}")
        return None
