import json
import boto3
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any

def get_prefix_before_english(filename: str) -> str:
    """Extract the word prefix from the filename"""
    parts = filename.split("_English")
    if parts:
        return parts[0]
    return filename

def process_results(results: List[Dict[str, Any]], successful_dict: defaultdict) -> List[str]:
    """Process a batch of results and return failed files"""
    failed_files = []
    
    if not results:
        return failed_files
        
    for result in results:
        if 'body' in result:
            # Process successful transcriptions
            if 'completed' in result['body']:
                for filename, transcription in result['body']['completed'].items():
                    prefix = get_prefix_before_english(filename)
                    successful_dict[prefix].add(transcription)
            
            # Collect failed files
            if 'retryable_uris' in result['body']:
                failed_files.extend(result['body']['retryable_uris'])
                
    return failed_files

def process_transcriptions(transcription_results: List[Dict], retry_results: List[Dict], 
                         output_bucket: str, output_prefix: str) -> Dict[str, Any]:
    """Process transcription results and generate success/failure files"""
    
    # Create dictionary for successful transcriptions
    successful_dict = defaultdict(set)
    failed_files = []
    
    # Process both initial and retry results
    failed_files.extend(process_results(transcription_results, successful_dict))
    failed_files.extend(process_results(retry_results, successful_dict))
    
    # Remove duplicates from failed files
    failed_files = list(set(failed_files))
    
    # Convert successful_dict sets to lists for JSON serialization
    successful_dict = {prefix: list(transcriptions) 
                      for prefix, transcriptions in successful_dict.items()}
    
    # Generate timestamps for filenames
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save successful transcriptions
    success_key = f"{output_prefix}successful_transcriptions_{timestamp}.json"
    s3_client = boto3.client('s3')
    s3_client.put_object(
        Bucket=output_bucket,
        Key=success_key,
        Body=json.dumps(successful_dict, indent=2, ensure_ascii=False)
    )
    
    # Save failed files list
    failed_key = f"{output_prefix}failed_files_{timestamp}.json"
    s3_client.put_object(
        Bucket=output_bucket,
        Key=failed_key,
        Body=json.dumps({
            'failed_files': failed_files,
            'count': len(failed_files)
        }, indent=2)
    )
    
    return {
        'successful_file': success_key,
        'failed_file': failed_key,
        'summary': {
            'successful_words': sum(len(transcriptions) 
                                  for transcriptions in successful_dict.values()),
            'failed_files': len(failed_files)
        }
    }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler function"""
    try:
        # Get environment variables
        output_bucket = os.environ['OUTPUT_BUCKET']
        output_prefix = os.environ['OUTPUT_PREFIX']
        
        # Get results from event with new structure
        transcription_results = event.get('transcription_results', {}).get('results', [])
        retry_results = event.get('retry_results', {}).get('results', [])
        
        # Process transcriptions
        result = process_transcriptions(
            transcription_results,
            retry_results,
            output_bucket,
            output_prefix
        )
        
        return {
            'statusCode': 200,
            'body': {
                'message': 'Processing completed',
                'result': result
            }
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {
                'error': str(e)
            }
        }
