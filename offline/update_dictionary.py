import json
from typing import Dict, List

def load_dictionary(path: str) -> Dict:
    with open(path, 'r') as f:
        return json.load(f)

def save_dictionary(path: str, dictionary: Dict):
    with open(path, 'w') as f:
        json.dump(dictionary, f, indent=2, ensure_ascii=False)

def update_dictionary(llm_dict_path: str, transcription_dict_path: str, output_path: str):
    llm_dict = load_dictionary(llm_dict_path)
    transcription_dict = load_dictionary(transcription_dict_path)
    
    updated_dict = {}
    
    for word, entry in llm_dict.items():
        if word in transcription_dict:
            updated_dict[word] = transcription_dict[word]
        else:
            updated_dict[word] = entry['v']
    
    save_dictionary(output_path, updated_dict)
    print(f"Updated dictionary saved to {output_path}")

def main():
    llm_dict_path = 'generated_dict/LLM_Generate/short_variations_dictionary.json'
    transcription_dict_path = 'generated_dict/TTS_STT_Generate/filtered_transcriptions_20241113_112422.json'
    output_path = 'generated_dict/LLM_Generate/updated_variations_dictionary.json'
    
    update_dictionary(llm_dict_path, transcription_dict_path, output_path)

if __name__ == "__main__":
    main()
