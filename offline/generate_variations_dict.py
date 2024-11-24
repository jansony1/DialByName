import json
from word_matcher import WordMatcher
from typing import Dict, List, Set
from difflib import SequenceMatcher

def calculate_variation_score(original: str, variation: str) -> float:
    """Calculate how likely a variation is to be used"""
    # Exact match gets highest score
    if original.lower() == variation.lower():
        return 1.0
    
    # Calculate string similarity
    string_sim = SequenceMatcher(None, original.lower(), variation.lower()).ratio()
    
    # Shorter variations are more likely to be used
    length_ratio = min(len(variation), len(original)) / max(len(variation), len(original))
    
    # Variations that preserve word boundaries are more likely
    word_boundary_score = 0.1
    if ' ' in original and ' ' in variation and len(original.split()) == len(variation.split()):
        word_boundary_score = 0.2
    
    return string_sim * 0.6 + length_ratio * 0.3 + word_boundary_score

def generate_variations_dictionary(input_dict_path: str, transcriptions_path: str) -> Dict:
    """Generate a dictionary of variations for each word"""
    
    # Initialize the word matcher
    matcher = WordMatcher(input_dict_path)
    
    # Load transcription results to get real-world variations
    with open(transcriptions_path, 'r') as f:
        transcriptions = json.load(f)
    
    # Create variations dictionary
    variations_dict = {}
    
    # Load original dictionary
    with open(input_dict_path, 'r') as f:
        original_dict = json.load(f)
    
    for item in original_dict:
        word = item['word']
        variations = set()
        
        # Add normalized form
        normalized = matcher._normalize_text(word)
        variations.add(normalized)
        
        # Add phonetic form
        phonetic = matcher._get_phonetic_key(word)
        variations.add(phonetic)
        
        # Add real transcription variations
        if word in transcriptions:
            for transcription in transcriptions[word]:
                clean_transcription = matcher._normalize_text(transcription)
                if clean_transcription:
                    variations.add(clean_transcription)
        
        # Score and sort variations
        scored_variations = [
            (var, calculate_variation_score(word, var))
            for var in variations
            if var  # Skip empty variations
        ]
        scored_variations.sort(key=lambda x: x[1], reverse=True)
        
        # Take top 3 variations
        top_variations = [var for var, _ in scored_variations[:3]]
        
        # Create simplified metadata
        word_parts = normalized.split()
        metadata = {
            "c": len(word_parts) > 1,  # c for compound
            "p": phonetic  # p for phonetic
        }
        
        variations_dict[word] = {
            "v": top_variations,  # v for variations
            "m": metadata  # m for metadata
        }
    
    return variations_dict

def main():
    # Input and output file paths
    input_dict_path = 'sample_file/modified_short_dict.json'
    transcriptions_path = 'grouped_transcriptions_20241112_160243.json'
    output_path = 'short_variations_dictionary.json'
    
    # Generate variations dictionary
    variations_dict = generate_variations_dictionary(input_dict_path, transcriptions_path)
    
    # Save to file with nice formatting
    with open(output_path, 'w') as f:
        json.dump(variations_dict, f, indent=2, ensure_ascii=False)
    
    print(f"Generated shortened variations dictionary saved to {output_path}")
    
    # Print some statistics
    total_words = len(variations_dict)
    total_variations = sum(len(entry["v"]) for entry in variations_dict.values())
    compound_words = sum(1 for entry in variations_dict.values() if entry["m"]["c"])
    
    print("\nDictionary Statistics:")
    print(f"Total words: {total_words}")
    print(f"Total variations: {total_variations}")
    print(f"Average variations per word: {total_variations/total_words:.2f}")
    print(f"Compound words: {compound_words}")
    
    # Print example entries
    print("\nExample Entries:")
    examples = list(variations_dict.keys())[:3]
    for word in examples:
        print(f"\n{word}:")
        print(json.dumps(variations_dict[word], indent=2))

if __name__ == "__main__":
    main()
