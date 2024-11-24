import os
import json
import boto3
import time
import urllib.request
from datetime import datetime
from multiprocessing import cpu_count
from botocore.exceptions import BotoCoreError, ClientError
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

# Initialize the S3 and Transcribe clients
s3_client = boto3.client('s3', region_name='us-west-2')
transcribe_client = boto3.client('transcribe', region_name='us-west-2')

# S3 bucket configuration
BASE_BUCKET_NAME = 'voice-matching-zytest'
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
S3_PREFIX = f"{TIMESTAMP}"
S3_BUCKET_PATH = f"{BASE_BUCKET_NAME}/{S3_PREFIX}"

# Determine optimal number of workers based on CPU cores
CPU_COUNT = cpu_count()
MAX_WORKERS = max(2, min(CPU_COUNT * 2, 10))  # At least 2, at most 10 workers
BATCH_SIZE = 10

print(f"System has {CPU_COUNT} CPU cores, using {MAX_WORKERS} workers")

def check_bucket_exists():
    try:
        s3_client.head_bucket(Bucket=BASE_BUCKET_NAME)
        print(f"S3 bucket '{BASE_BUCKET_NAME}' exists and is accessible.")
        return True
    except Exception as e:
        print(f"Error checking S3 bucket: {e}")
        return False

def upload_to_s3(file_path: str) -> Tuple[str, str]:
    """Upload a file to S3 and return tuple of (filename, s3_uri or error message)"""
    try:
        file_name = os.path.basename(file_path)
        s3_key = f"{S3_PREFIX}/{file_name}"
        s3_client.upload_file(file_path, BASE_BUCKET_NAME, s3_key)
        s3_uri = f"s3://{BASE_BUCKET_NAME}/{s3_key}"
        print(f"Successfully uploaded {file_name} to {s3_uri}")
        return file_name, s3_uri
    except Exception as e:
        error_msg = f"Failed to upload to S3: {str(e)}"
        print(f"Error uploading {file_path}: {error_msg}")
        return os.path.basename(file_path), error_msg

def start_transcription_job(job_info: Tuple[str, str]) -> Tuple[str, str, str]:
    """Start a transcription job and return tuple of (filename, job_name, status)"""
    filename, file_uri = job_info
    try:
        job_name = f"transcribe_job_{TIMESTAMP}_{filename.replace('.mp3', '')}"
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': file_uri},
            MediaFormat='mp3',
            LanguageCode='en-US'
        )
        print(f"Started transcription job: {job_name}")
        return filename, job_name, "STARTED"
    except Exception as e:
        error_msg = f"Failed to start job: {str(e)}"
        print(f"Error starting transcription for {filename}: {error_msg}")
        return filename, "", error_msg

def check_job_status(job_info: Tuple[str, str, str]) -> Tuple[str, str]:
    """Check transcription job status and return tuple of (filename, transcript or status)"""
    filename, job_name, _ = job_info
    try:
        while True:
            status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            job_status = status['TranscriptionJob']['TranscriptionJobStatus']
            
            if job_status == 'COMPLETED':
                transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
                with urllib.request.urlopen(transcript_uri) as response:
                    transcript_json = json.loads(response.read().decode('utf-8'))
                    return filename, transcript_json['results']['transcripts'][0]['transcript']
                    
            elif job_status == 'FAILED':
                error_msg = status['TranscriptionJob'].get('FailureReason', 'Unknown failure')
                print(f"Transcription job failed for {filename}: {error_msg}")
                return filename, f"Transcription failed: {error_msg}"
                
            time.sleep(5)
            
    except Exception as e:
        error_msg = f"Error checking status: {str(e)}"
        print(f"Error getting transcription result for {filename}: {error_msg}")
        return filename, error_msg

def process_batch(files: List[str]) -> Dict[str, str]:
    """Process a batch of files through the entire pipeline"""
    results = {}
    
    # Step 1: Upload files to S3 in parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        upload_futures = [executor.submit(upload_to_s3, f) for f in files]
        upload_results = [future.result() for future in as_completed(upload_futures)]
    
    # Filter successful uploads
    successful_uploads = [(f, uri) for f, uri in upload_results if uri.startswith('s3://')]
    
    # Add failed uploads to results
    failed_uploads = [(f, msg) for f, msg in upload_results if not msg.startswith('s3://')]
    for filename, error_msg in failed_uploads:
        results[filename] = error_msg
    
    if not successful_uploads:
        return results
    
    # Step 2: Start transcription jobs in parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        job_futures = [executor.submit(start_transcription_job, upload) for upload in successful_uploads]
        job_results = [future.result() for future in as_completed(job_futures)]
    
    # Filter successfully started jobs
    successful_jobs = [(f, j, s) for f, j, s in job_results if s == "STARTED"]
    
    # Add failed job starts to results
    failed_jobs = [(f, s) for f, j, s in job_results if s != "STARTED"]
    for filename, error_msg in failed_jobs:
        results[filename] = error_msg
    
    if not successful_jobs:
        return results
    
    # Step 3: Check job status and get transcriptions in parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        status_futures = [executor.submit(check_job_status, job) for job in successful_jobs]
        status_results = [future.result() for future in as_completed(status_futures)]
    
    # Add all results
    for filename, result in status_results:
        results[filename] = result
    
    return results

def main():
    print(f"Starting the parallel transcription process...")
    print(f"Using S3 path: {S3_BUCKET_PATH}")
    print(f"Using {MAX_WORKERS} parallel workers")
    
    if not check_bucket_exists():
        print(f"Error: S3 bucket '{BASE_BUCKET_NAME}' does not exist or is not accessible.")
        return

    # Get list of MP3 files from audio_file directory
    audio_dir = 'audio_file'
    audio_files = [os.path.join(audio_dir, f) for f in os.listdir(audio_dir) if f.endswith('.mp3')]
    total_files = len(audio_files)
    print(f"Found {total_files} MP3 files to process in {audio_dir}")

    # Process files in batches
    all_results = {}
    for i in range(0, total_files, BATCH_SIZE):
        batch = audio_files[i:i + BATCH_SIZE]
        print(f"\nProcessing batch {i//BATCH_SIZE + 1} ({len(batch)} files)...")
        batch_results = process_batch(batch)
        all_results.update(batch_results)
        
        # Save intermediate results
        results_filename = f'transcription_results_{TIMESTAMP}.json'
        with open(results_filename, 'w') as json_file:
            json.dump(all_results, json_file, indent=2)
        print(f"Saved intermediate results to {results_filename}")

    print("\nTranscription process complete.")

if __name__ == "__main__":
    main()
