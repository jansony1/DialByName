import json
from difflib import SequenceMatcher
import re

def normalize_text(text):
    return re.sub(r'[^\w\s]', '', text.lower())

def get_phonetic_key(text):
    text = text.lower()
    patterns = {
        'ph': 'f', 'ough': 'o', 'ck': 'k', 'gh': '', 'kn': 'n', 'wr': 'r',
        'mb': 'm', 'wh': 'w', 'qu': 'kw', 'x': 'ks'
    }
    for pattern, replacement in patterns.items():
        text = text.replace(pattern, replacement)
    return ''.join(c for c in text if c not in 'aeiou')

def calculate_similarity(s1, s2):
    return SequenceMatcher(None, s1, s2).ratio()

def match_text(text, dictionary):
    text = normalize_text(text)
    text_phonetic = get_phonetic_key(text)
    
    best_match = None
    best_similarity = 0
    best_match_type = None

    for word, entry in dictionary.items():
        # Fast rejection
        if len(text) < 3 or (entry['m']['c'] and len(text.split()) < 2):
            continue
        
        if calculate_similarity(text_phonetic, entry['m']['p']) < 0.5:
            continue
        
        # Detailed matching
        for variation in entry['v']:
            # Exact match
            if text == normalize_text(variation):
                return {
                    "Matched Word": word,
                    "Match Type": "Exact",
                    "Confidence": "High"
                }
            
            # Partial match
            similarity = calculate_similarity(text, normalize_text(variation))
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = word
                best_match_type = "Partial"
        
        # Phonetic match
        phonetic_similarity = calculate_similarity(text_phonetic, get_phonetic_key(word))
        if phonetic_similarity > best_similarity:
            best_similarity = phonetic_similarity
            best_match = word
            best_match_type = "Phonetic"
    
    if best_match and best_similarity >= 0.5:
        confidence = "High" if best_similarity > 0.8 else "Medium" if best_similarity > 0.6 else "Low"
        return {
            "Matched Word": best_match,
            "Match Type": best_match_type,
            "Confidence": confidence
        }
    
    return "No match found"

def main():
    # Load dictionary
    with open('short_variations_dictionary.json', 'r') as f:
        dictionary = json.load(f)
    
    # Load test cases
    with open('test_prompt.py', 'r') as f:
        exec(f.read(), globals())
    test_cases = load_test_cases()
    
    print("Running Matcher on Test Cases")
    print("-" * 50)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}:")
        print(f"Input: {test['input']}")
        result = match_text(test['input'], dictionary)
        print(f"Result: {json.dumps(result, indent=2)}")
        print(f"Expected: {json.dumps(test['expected'], indent=2)}")
        print(f"Match: {'Yes' if result == test['expected'] else 'No'}")
        print("-" * 30)

if __name__ == "__main__":
    main()
