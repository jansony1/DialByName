import os
import json
import boto3
import time
import urllib.request
from datetime import datetime
from multiprocessing import cpu_count
from botocore.exceptions import BotoCoreError, ClientError
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Any

# Initialize the S3 and Transcribe clients
s3_client = boto3.client('s3', region_name='us-west-2')
transcribe_client = boto3.client('transcribe', region_name='us-west-2')

# S3 bucket configuration
BASE_BUCKET_NAME = 'voice-matching-zytest'
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
S3_PREFIX = f"{TIMESTAMP}"
S3_BUCKET_PATH = f"{BASE_BUCKET_NAME}/{S3_PREFIX}"

# Constants
MAX_WORKERS = 10  # Maximum number of parallel jobs per Lambda

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

def process_batch(s3_uris: List[str], is_retry: bool = False) -> Dict[str, Any]:
    """Process a batch of S3 URIs through the transcription pipeline"""
    results = {
        'completed': {},      # 成功完成的转录
        'retryable_uris': [], # 需要重试的URI
        'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
    }
    
    # Ensure s3_uris is a list of strings
    if not s3_uris:
        return results
        
    # Print debug info
    print(f"Processing s3_uris: {s3_uris}, type: {type(s3_uris)}")
    
    # Extract filenames from S3 URIs
    file_infos = []
    for uri in s3_uris:
        try:
            filename = os.path.basename(uri)
            file_infos.append((filename, uri))
        except Exception as e:
            print(f"Error processing URI {uri}: {str(e)}")
            continue
    
    # Start transcription jobs in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        job_futures = [executor.submit(start_transcription_job, file_info) for file_info in file_infos]
        job_results = [future.result() for future in as_completed(job_futures)]
    
    # Process job start results
    successful_jobs = []
    for filename, job_name, status in job_results:
        if status == "STARTED":
            successful_jobs.append((filename, job_name, status))
        elif "limit exceeded" in str(status).lower() and not is_retry:
            # 只有在非重试状态下才添加到重试列表
            results['retryable_uris'].append(next(uri for fn, uri in file_infos if fn == filename))
    
    if successful_jobs:
        # Check job status and get transcriptions
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            status_futures = [executor.submit(check_job_status, job) for job in successful_jobs]
            status_results = [future.result() for future in as_completed(status_futures)]
        
        # Process transcription results
        for filename, result in status_results:
            if "limit exceeded" in str(result).lower() and not is_retry:
                # 找到对应的URI并添加到重试列表
                results['retryable_uris'].append(next(uri for fn, uri in file_infos if fn == filename))
            elif not result.startswith("Transcription failed") and not result.startswith("Error"):
                results['completed'][filename] = result
    
    return results

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler function"""
    try:
        # Get chunk and retry flag from event
        chunk = event.get('chunk', [])
        is_retry = event.get('is_retry', False)
        
        if not chunk:
            raise ValueError("No chunk data provided in event")
            
        # Process the batch of URIs
        results = process_batch(chunk, is_retry)
        
        return {
            'statusCode': 200,
            'body': {
                'message': 'Transcription batch processed',
                'batch_id': results['timestamp'],
                'completed': results['completed'],
                'retryable_uris': results['retryable_uris']
            }
        }
    except Exception as e:
        error_msg = str(e)
        print(f"Error processing batch: {error_msg}")
        return {
            'statusCode': 500,
            'body': {
                'error': error_msg,
                'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
            }
        }
