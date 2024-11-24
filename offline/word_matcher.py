import json
import re
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Optional

class WordMatcher:
    def __init__(self, dictionary_path: str):
        self.dictionary = self._load_dictionary(dictionary_path)
        self.word_variations = self._generate_variations()
        # Generic terms that should have lower matching priority
        self.generic_terms = {'bar', 'store', 'shop', 'coffee', 'juice', 'restaurant', 'cafe', 'market'}
        
    def _load_dictionary(self, path: str) -> List[str]:
        """Load and process dictionary words"""
        with open(path, 'r') as f:
            data = json.load(f)
        return [item['word'] for item in data]
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        # Remove punctuation and convert to lowercase
        text = re.sub(r'[^\w\s]', '', text.lower())
        # Replace multiple spaces with single space
        return re.sub(r'\s+', ' ', text).strip()
    
    def _get_phonetic_key(self, text: str) -> str:
        """Generate a simplified phonetic key for text"""
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
            'ch': 'k',
            'tch': 'ch',
            'th': 't',
            'sh': 's',
            'zh': 'j',
            'dg': 'j'
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
    
    def _generate_variations(self) -> Dict[str, List[str]]:
        """Generate variations for each dictionary word"""
        variations = {}
        
        for word in self.dictionary:
            word_variations = set()
            normalized_word = self._normalize_text(word)
            
            # Add original and normalized forms
            word_variations.add(word.lower())
            word_variations.add(normalized_word)
            
            # Add common variations
            word_parts = normalized_word.split()
            
            # Handle compound words
            if len(word_parts) > 1:
                # Add with different separators
                word_variations.add(''.join(word_parts))
                word_variations.add('-'.join(word_parts))
                word_variations.add('_'.join(word_parts))
                
                # Add partial matches for significant word combinations
                for i in range(len(word_parts)):
                    for j in range(i + 1, len(word_parts) + 1):
                        subset = ' '.join(word_parts[i:j])
                        if len(subset) > 2 and subset.lower() not in {'the', 'and', 'or', 'in', 'at', 'of'}:
                            word_variations.add(subset)
                
                # Add individual significant words
                for part in word_parts:
                    if len(part) > 2 and part.lower() not in {'the', 'and', 'or', 'in', 'at', 'of'}:
                        word_variations.add(part)
            
            # Add phonetic variations
            phonetic = self._get_phonetic_key(normalized_word)
            word_variations.add(phonetic)
            
            # Add common STT errors
            # Replace similar sounding letters/combinations
            stt_replacements = {
                'v': 'b',
                'm': 'n',
                'p': 'b',
                't': 'd',
                'g': 'k',
                'ch': 'j',
                'sh': 's',
                'z': 's',
                'f': 'v',
                'b': 'v',
                'd': 't',
                'j': 'g'
            }
            
            for part in word_parts:
                for old, new in stt_replacements.items():
                    if old in part.lower():
                        new_part = part.lower().replace(old, new)
                        word_variations.add(new_part)
                        # Also add the variation to compound words
                        if len(word_parts) > 1:
                            new_parts = word_parts.copy()
                            new_parts[word_parts.index(part)] = new_part
                            word_variations.add(' '.join(new_parts))
            
            variations[word] = list(word_variations)
        
        return variations
    
    def _calculate_word_similarity(self, word1: str, word2: str) -> float:
        """Calculate similarity between two words"""
        # Calculate string similarity
        string_sim = SequenceMatcher(None, word1, word2).ratio()
        
        # Calculate phonetic similarity
        phonetic_sim = SequenceMatcher(None, 
                                     self._get_phonetic_key(word1),
                                     self._get_phonetic_key(word2)).ratio()
        
        # Calculate substring similarity
        substr_sim = 0.0
        if len(word1) > 3 and len(word2) > 3:
            if word1 in word2 or word2 in word1:
                substr_sim = 0.9
        
        return max(string_sim, phonetic_sim, substr_sim)
    
    def _calculate_similarity(self, input_text: str, dict_word: str, variation: str) -> Tuple[float, str]:
        """Calculate similarity score and determine match type"""
        input_text = input_text.lower()
        dict_word = dict_word.lower()
        variation = variation.lower()
        
        # Check for exact match
        if input_text == variation:
            return 1.0, "Exact"
        
        # Split into words
        input_words = input_text.split()
        dict_words = dict_word.split()
        
        # Calculate string similarity
        string_similarity = SequenceMatcher(None, input_text, variation).ratio()
        
        # Calculate phonetic similarity
        phonetic_similarity = SequenceMatcher(None, 
                                            self._get_phonetic_key(input_text),
                                            self._get_phonetic_key(variation)).ratio()
        
        # Calculate word-by-word similarity
        word_similarity = 0.0
        if input_words:
            # Find best matches for each input word
            word_matches = []
            for input_word in input_words:
                # Find best match among dictionary words
                best_match = max(
                    self._calculate_word_similarity(input_word, dict_word)
                    for dict_word in dict_words
                )
                
                # Apply weight based on word type
                weight = 0.5 if input_word in self.generic_terms else 1.0
                word_matches.append(best_match * weight)
            
            word_similarity = sum(word_matches) / len(word_matches)
            
            # Boost similarity for significant word matches
            significant_input = [w for w in input_words if w not in self.generic_terms]
            significant_dict = [w for w in dict_words if w not in self.generic_terms]
            
            if significant_input and significant_dict:
                sig_matches = []
                for sig_in in significant_input:
                    best_sig = max(
                        self._calculate_word_similarity(sig_in, sig_dict)
                        for sig_dict in significant_dict
                    )
                    sig_matches.append(best_sig)
                
                sig_similarity = sum(sig_matches) / len(sig_matches)
                if sig_similarity > 0.7:  # Lowered threshold for significant words
                    word_similarity = max(word_similarity, sig_similarity)
                    
                    # Extra boost if significant words match in order
                    if len(significant_input) > 1 and len(significant_dict) > 1:
                        input_order = ' '.join(significant_input)
                        dict_order = ' '.join(significant_dict)
                        if input_order in dict_order or dict_order in input_order:
                            word_similarity = min(1.0, word_similarity + 0.1)
        
        # Penalize matches that are only generic terms
        if all(word in self.generic_terms for word in input_words):
            string_similarity *= 0.5
            phonetic_similarity *= 0.5
            word_similarity *= 0.5
        
        # Use the highest similarity score
        max_similarity = max(string_similarity, phonetic_similarity, word_similarity)
        
        # Determine match type
        if max_similarity == string_similarity:
            match_type = "Partial"
        else:
            match_type = "Phonetic"
        
        return max_similarity, match_type
    
    def _calculate_confidence(self, similarity: float, match_type: str) -> str:
        """Calculate confidence level based on similarity score and match type"""
        if match_type == "Exact":
            return "High"
        elif match_type == "Partial":
            if similarity >= 0.8:
                return "High"
            elif similarity >= 0.6:
                return "Medium"
            else:
                return "Low"
        else:  # Phonetic
            if similarity >= 0.7:
                return "High"
            elif similarity >= 0.5:
                return "Medium"
            else:
                return "Low"
    
    def match_text(self, input_text: str) -> Optional[Dict]:
        """
        Match input text against dictionary words and their variations.
        Returns match details or None if no match found.
        """
        input_text = self._normalize_text(input_text)
        input_words = input_text.split()
        
        best_match = None
        best_similarity = 0
        best_match_type = None
        
        # First try to find exact matches
        for dict_word, variations in self.word_variations.items():
            if input_text in variations:
                # For exact matches of a single word, prefer entries where it's the first word
                dict_normalized = self._normalize_text(dict_word)
                dict_words = dict_normalized.split()
                if len(input_words) == 1 and len(dict_words) > 1:
                    # If the input matches the first word of the dictionary entry exactly
                    if dict_words[0] == input_text:
                        return {
                            "Matched Word": dict_word,
                            "Match Type": "Exact",
                            "Confidence": "High"
                        }
                else:
                    return {
                        "Matched Word": dict_word,
                        "Match Type": "Exact",
                        "Confidence": "High"
                    }
        
        # Then try partial and phonetic matches
        for dict_word, variations in self.word_variations.items():
            dict_normalized = self._normalize_text(dict_word)
            dict_words = dict_normalized.split()
            
            # Calculate similarity scores
            similarity = 0.0
            match_type = None
            
            # Check if input contains significant words from dictionary entry
            significant_dict_words = [w for w in dict_words if w not in self.generic_terms]
            significant_input_words = [w for w in input_words if w not in self.generic_terms]
            
            # First try matching significant words
            if significant_dict_words and significant_input_words:
                sig_matches = []
                for sig_input in significant_input_words:
                    best_sig_match = max(
                        self._calculate_word_similarity(sig_input, sig_dict)
                        for sig_dict in significant_dict_words
                    )
                    sig_matches.append(best_sig_match)
                
                if sig_matches:
                    sig_similarity = sum(sig_matches) / len(sig_matches)
                    if sig_similarity > 0.7:  # Lowered threshold for significant words
                        similarity = sig_similarity
                        match_type = "Partial"
                        
                        # Extra boost if significant words match in order
                        if len(significant_input_words) > 1 and len(significant_dict_words) > 1:
                            input_order = ' '.join(significant_input_words)
                            dict_order = ' '.join(significant_dict_words)
                            if input_order in dict_order or dict_order in input_order:
                                similarity = min(1.0, similarity + 0.1)
            
            # Check variations if no good significant word match
            if similarity < 0.8:
                for variation in variations:
                    var_similarity, var_match_type = self._calculate_similarity(input_text, dict_word, variation)
                    if var_similarity > similarity:
                        similarity = var_similarity
                        match_type = var_match_type
            
            # Apply length penalty for compound words
            if len(dict_words) > 1:
                # Smaller penalty when input matches first word or contains significant words
                if dict_words[0] in input_words or any(w in significant_dict_words for w in input_words):
                    length_penalty = 0.05
                else:
                    length_penalty = 0.1 * abs(len(dict_words) - len(input_words))
                similarity = max(0, similarity - length_penalty)
            
            # Boost matches that contain all input words (in any order)
            input_set = set(input_words)
            dict_set = set(dict_words)
            if input_set.issubset(dict_set):
                similarity = min(1.0, similarity + 0.1)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = dict_word
                best_match_type = match_type
        
        if best_match and best_similarity >= 0.5:
            confidence = self._calculate_confidence(best_similarity, best_match_type)
            return {
                "Matched Word": best_match,
                "Match Type": best_match_type,
                "Confidence": confidence
            }
        
        return None

def main():
    # Initialize the matcher with the dictionary
    matcher = WordMatcher('sample_file/modified_short_dict.json')
    
    # Example usage
    test_inputs = [
        "apple store",
        "haagen dazs",
        "lululemmon",
        "see butter",
        "shake shak",
        "tifany",
        "barns and noble",
        "the cheesecake",
        "guchy",
        "nike",
        "juice bar",
        "coffee shop"
    ]
    
    print("Word Matching System")
    print("-" * 50)
    
    for input_text in test_inputs:
        print(f"\nInput: {input_text}")
        result = matcher.match_text(input_text)
        if result:
            print(f"Matched Word: {result['Matched Word']}")
            print(f"Match Type: {result['Match Type']}")
            print(f"Confidence: {result['Confidence']}")
        else:
            print("No match found")

if __name__ == "__main__":
    main()
