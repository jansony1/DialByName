import boto3
import json
import os
from botocore.exceptions import BotoCoreError, ClientError

# Initialize the Polly client with a specific region
polly_client = boto3.client('polly', region_name='us-west-2')

def load_input_data(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        return []
    except json.JSONDecodeError:
        print(f"Error: The file {file_path} contains invalid JSON.")
        return []

def get_compatible_voices(language_code):
    try:
        response = polly_client.describe_voices(LanguageCode=language_code)
        return [voice['Id'] for voice in response['Voices'] if 'SupportedEngines' in voice and 'standard' in voice['SupportedEngines']]
    except (BotoCoreError, ClientError) as error:
        print(f"Error getting voices: {error}")
        return []

def generate_audio(text, voice_id, lang_code, polly_client=None):
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

def main():
    # Create audio_file directory if it doesn't exist
    os.makedirs('audio_file', exist_ok=True)
    
    input_data = load_input_data('input_words.json')
    if not input_data:
        print("No input data available. Exiting.")
        return

    languages = {
        'en-US': 'English, US',
        'en-GB': 'English, British',
        'en-IN': 'English, Indian',
        'en-NZ': 'English, New Zealand',
        'en-ZA': 'English, South African',
        'en-ZA': 'English, Australian',
    }

    for item in input_data:
        word = item['word']
        for lang_code, lang_name in languages.items():
            voices = get_compatible_voices(lang_code)
            for voice in voices:
                audio_content = generate_audio(word, voice, lang_code)
                if audio_content:
                    filename = f"audio_file/{word.replace(' ', '_')}_{lang_name.replace(', ', '_')}_{voice}.mp3"
                    with open(filename, 'wb') as file:
                        file.write(audio_content)
                    print(f"Generated audio file: {filename}")

if __name__ == "__main__":
    main()
