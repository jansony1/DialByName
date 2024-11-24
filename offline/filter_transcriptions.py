import json
from datetime import datetime
from difflib import SequenceMatcher
import re

def normalize_text(text):
    """Normalize text by removing punctuation and converting to lowercase"""
    return re.sub(r'[^\w\s]', '', text.lower())

def is_exact_match(key, value):
    """Check if the value is an exact match with the key"""
    key = normalize_text(key)
    value = normalize_text(value)
    return key == value

def get_similarity_ratio(str1, str2):
    """Get similarity ratio between two strings"""
    return SequenceMatcher(None, normalize_text(str1), normalize_text(str2)).ratio()

def is_high_confidence_partial_match(key, value, threshold=0.65):
    """Check if the value is a high-confidence partial match with the key"""
    # Split compound store names and check each part
    key_parts = key.replace('_', ' ').lower().split()
    value_parts = value.lower().split()
    
    # Check if any key part has a high similarity with any value part
    for key_part in key_parts:
        for value_part in value_parts:
            if get_similarity_ratio(key_part, value_part) >= threshold:
                return True
    
    # Also check full string similarity
    return get_similarity_ratio(key.replace('_', ' '), value) >= threshold

def get_phonetic_key(text):
    """Convert text to a simplified phonetic representation"""
    text = text.lower()
    
    # Common sound pattern replacements
    patterns = {
        'ph': 'f',
        'ough': 'o',
        'gh': '',
        'kn': 'n',
        'wr': 'r',
        'mb': 'm',
        'ce': 's',
        'ci': 's',
        'cy': 's',
        'ge': 'j',
        'gi': 'j',
        'gy': 'j',
        'chr': 'kr',
        'ck': 'k',
        'cc': 'k',
        'que': 'k',
        'x': 'ks',
        'wh': 'w',
        'rh': 'r',
        'ae': 'e',
        'oe': 'e',
        'eau': 'o',
        'au': 'o',
        'ou': 'u',
        'oo': 'u',
        'ee': 'i',
        'ea': 'i',
        'ai': 'ay',
        'ay': 'ay',
        'ey': 'ay',
    }
    
    result = text
    for pattern, replacement in patterns.items():
        result = result.replace(pattern, replacement)
    
    # Remove duplicate consecutive letters
    result = re.sub(r'(.)\1+', r'\1', result)
    
    # Remove most vowels except at the start of words
    words = result.split()
    processed_words = []
    for word in words:
        if word:
            # Keep first letter if it's a vowel
            first_char = word[0]
            rest = word[1:]
            # Remove vowels from rest of word
            rest = re.sub(r'[aeiou]', '', rest)
            processed_words.append(first_char + rest)
    
    return ' '.join(processed_words)

def is_phonetically_similar(key, value):
    """Check if the value is phonetically similar to the key"""
    # Convert store name format to normal text
    key = key.replace('_', ' ')
    
    # Get phonetic keys
    key_phonetic = get_phonetic_key(key)
    value_phonetic = get_phonetic_key(value)
    
    # Compare phonetic representations
    similarity = get_similarity_ratio(key_phonetic, value_phonetic)
    return similarity >= 0.6

def should_keep_transcription(key, value):
    """Determine if a transcription should be kept based on all criteria"""
    # Remove trailing punctuation and normalize
    value = re.sub(r'[.?!]$', '', value).strip()
    key = key.replace('_', ' ')
    
    return (is_exact_match(key, value) or 
            is_high_confidence_partial_match(key, value) or 
            is_phonetically_similar(key, value))

def filter_transcriptions(input_file, output_file):
    """Filter transcriptions based on similarity criteria"""
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    filtered_data = {}
    
    for key, values in data.items():
        # Keep all store names but filter their values
        filtered_values = [value for value in values if should_keep_transcription(key, value)]
        filtered_data[key] = filtered_values
    
    # Write filtered data to output file
    with open(output_file, 'w') as f:
        json.dump(filtered_data, f, indent=2)

def main():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    input_file = 'grouped_transcriptions_20241112_160243.json'
    output_file = f'filtered_transcriptions_{timestamp}.json'
    
    print(f"Filtering transcriptions from {input_file}")
    filter_transcriptions(input_file, output_file)
    print(f"Filtered transcriptions saved to {output_file}")

if __name__ == "__main__":
    main()
