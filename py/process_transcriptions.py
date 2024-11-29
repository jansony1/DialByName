import json
import glob
import os
from collections import defaultdict
from datetime import datetime

def get_prefix_before_english(filename):
    # Split by "_English" and take the part before it
    parts = filename.split("_English")
    if parts:
        return parts[0]
    return filename

def get_closest_transcription_file():
    # Get all files matching the pattern
    pattern = "transcription_results_*.json"
    files = glob.glob(pattern)
    print(f"Looking for files matching pattern: {pattern}")
    print(f"Found files: {files}")
    
    if not files:
        # Try listing directory contents
        print("No files found with glob, listing directory contents:")
        print(os.listdir('.'))
        raise Exception("No transcription results files found")
    
    # Get current timestamp
    current_time = datetime.now()
    print(f"Current time: {current_time}")
    
    # Parse timestamps from filenames and find closest
    closest_file = None
    smallest_diff = float('inf')
    
    for file in files:
        try:
            # Extract timestamp from filename (format: transcription_results_YYYYMMDD_HHMMSS.json)
            timestamp_str = '_'.join(file.replace('.json', '').split('_')[2:])  # Get YYYYMMDD_HHMMSS part
            print(f"Processing file {file}, timestamp string: {timestamp_str}")
            file_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            
            # Calculate time difference
            time_diff = abs((current_time - file_time).total_seconds())
            print(f"Time difference: {time_diff} seconds")
            
            if time_diff < smallest_diff:
                smallest_diff = time_diff
                closest_file = file
                print(f"New closest file: {file}")
        except (IndexError, ValueError) as e:
            print(f"Error processing file {file}: {str(e)}")
            continue
    
    if not closest_file:
        raise Exception("No valid transcription results files found")
    
    print(f"Selected closest transcription file: {closest_file}")
    return closest_file

def process_transcriptions(output_file):
    # Get the closest transcription results file
    input_file = get_closest_transcription_file()
    print(f"Processing transcriptions from: {input_file}")
    
    # Read the input JSON file
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Create a defaultdict to group transcriptions by prefix
    grouped_data = defaultdict(set)
    
    # Process each item in the input data
    for filename, transcription in data.items():
        prefix = get_prefix_before_english(filename)
        # Only add non-failed transcriptions
        if isinstance(transcription, str) and not transcription.startswith("Transcription failed") and not transcription.startswith("Failed to"):
            grouped_data[prefix].add(transcription)
    
    # Convert sets to lists for JSON serialization
    result = {prefix: list(transcriptions) for prefix, transcriptions in grouped_data.items()}
    
    # Write the result to the output file
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"Grouped transcriptions saved to: {output_file}")

if __name__ == "__main__":
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"grouped_transcriptions_{timestamp}.json"
    process_transcriptions(output_file)
