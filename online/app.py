import streamlit as st
import boto3
import json
import time
import logging
import requests
import re
from botocore.exceptions import ClientError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_bedrock_response(text):
    """Parse Bedrock response text into structured format"""
    try:
        if isinstance(text, list) and len(text) > 0:
            text = text[0].get('text', '')
            
        # Extract values using regex and remove square brackets
        matched_word = re.search(r'Matched Word:[\s]*\[?(.*?)\]?(?:\n|$)', text)
        match_type = re.search(r'Match Type:[\s]*\[?(.*?)\]?(?:\n|$)', text)
        confidence = re.search(r'Confidence:[\s]*\[?(.*?)\]?(?:\n|$)', text)
        
        # Create structured response
        response = {
            "matched_word": matched_word.group(1) if matched_word else None,
            "match_type": match_type.group(1) if match_type else None,
            "confidence": confidence.group(1) if confidence else None
        }
        
        # If no match found
        if "No match found" in text:
            response = {
                "matched_word": None,
                "match_type": "No Match",
                "confidence": "Low"
            }
        
        logger.info(f"Parsed text: {text}")
        logger.info(f"Parsed response: {response}")
        return response
    except Exception as e:
        logger.error(f"Error parsing Bedrock response: {str(e)}")
        return {
            "matched_word": None,
            "match_type": None,
            "confidence": None,
            "error": str(e)
        }

def create_aws_session():
    """Create AWS session and clients"""
    try:
        session = boto3.Session(
            aws_access_key_id=st.session_state.aws_access_key,
            aws_secret_access_key=st.session_state.aws_secret_key,
            region_name=st.session_state.aws_region
        )
        st.session_state.session = session
        st.session_state.transcribe = session.client('transcribe')
        st.session_state.bedrock_runtime = session.client('bedrock-runtime')
        return True
    except ClientError as e:
        logger.error(f"AWS client error: {str(e)}")
        st.error(f"AWS authentication error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error creating AWS session: {str(e)}")
        st.error(f"Error: {str(e)}")
        return False

def configure_aws():
    st.session_state.aws_access_key = st.text_input("AWS Access Key ID", type="password")
    st.session_state.aws_secret_key = st.text_input("AWS Secret Access Key", type="password")
    st.session_state.aws_region = st.text_input("AWS Region", value="us-west-2")
    
    if st.button("Save AWS Configuration"):
        return create_aws_session()
    return False

def init_aws_clients():
    if 'aws_configured' not in st.session_state:
        st.session_state.aws_configured = False
        st.session_state.aws_access_key = ""
        st.session_state.aws_secret_key = ""
        st.session_state.aws_region = "us-west-2"
    
    if not st.session_state.aws_configured:
        st.warning("Please configure AWS credentials first")
        if configure_aws():
            st.session_state.aws_configured = True
            return True
        return False
    return True

# Initialize session state
if 'responses' not in st.session_state:
    st.session_state.responses = []
if 'system_prompt' not in st.session_state:
    st.session_state.system_prompt = """You are an AI assistant for fast text matching against a predefined dictionary.

Follow these guidelines:
1. Input Processing:
   - Convert input to lowercase
   - Remove any special characters
   - Keep only alphanumeric characters and spaces

2. Matching Process:
   - First try exact match (case-insensitive)
   - Then try partial match (if word is part of store name)
   - Consider common variations (e.g., "and" vs "&")
   - Handle abbreviations (e.g., "dept" for "department")

3. Confidence Scoring:
   - Exact match: High confidence
   - Partial match: Medium confidence
   - Abbreviation match: Medium confidence
   - No clear match: Low confidence

4. Output Format:
   For matches:
      Matched Word: <store name>
      Match Type: <Exact/Partial/Abbreviation>
      Confidence: <High/Medium/Low>
   
   For no matches:
      "No match found"

Return only the matching result without explanation."""

def call_bedrock(transcript, system_prompt):
    """Call Bedrock with transcribed text"""
    logger.info("Preparing Bedrock request...")
    
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "temperature": 0.7,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": transcript
            }
        ]
    })
    
    logger.info("Calling Bedrock API...")
    try:
        response = st.session_state.bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            contentType='application/json',
            accept='application/json',
            body=body
        )
        
        logger.info("Processing Bedrock response...")
        response_body = json.loads(response.get('body').read())
        logger.info(f"Raw Bedrock response: {response_body}")
        
        if 'messages' in response_body and len(response_body['messages']) > 0:
            content = response_body['messages'][0].get('content', [])
            if isinstance(content, list) and len(content) > 0:
                text = content[0].get('text', 'No response')
            else:
                text = content if isinstance(content, str) else 'No response'
        else:
            text = response_body.get('content', 'No response')
            
        # Parse response into structured format
        structured_response = parse_bedrock_response(text)
        logger.info(f"Structured Bedrock response: {json.dumps(structured_response, indent=2)}")
        return structured_response
        
    except Exception as e:
        logger.error(f"Error in Bedrock API call: {str(e)}")
        st.error(f"Error calling Bedrock: {str(e)}")
        return {
            "matched_word": None,
            "match_type": None,
            "confidence": None,
            "error": str(e)
        }

def process_s3_audio(s3_uri):
    """Process audio file from S3"""
    try:
        # Start transcription job
        job_name = f"transcription_{int(time.time())}"
        st.session_state.transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': s3_uri},
            MediaFormat=s3_uri.split('.')[-1].lower(),
            LanguageCode='en-US'
        )
        
        # Show progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Wait for transcription to complete
        while True:
            try:
                status = st.session_state.transcribe.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                job_status = status['TranscriptionJob']['TranscriptionJobStatus']
                
                if job_status == 'COMPLETED':
                    progress_bar.progress(100)
                    status_text.text("Transcription completed!")
                    break
                elif job_status == 'FAILED':
                    error_msg = status['TranscriptionJob'].get('FailureReason', 'Unknown error')
                    st.error(f"Transcription failed: {error_msg}")
                    return None
                else:
                    progress_bar.progress(50)
                    status_text.text(f"Transcription status: {job_status}")
                    time.sleep(5)
            except ClientError as e:
                st.error(f"AWS error: {str(e)}")
                logger.error(f"AWS error in transcription job: {str(e)}")
                return None
        
        # Get transcription results
        transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
        transcript_response = requests.get(transcript_uri)
        transcript_data = transcript_response.json()
        
        # Log transcription results
        transcript = transcript_data['results']['transcripts'][0]['transcript']
        logger.info(f"Transcription result: {transcript}")
        
        return transcript
            
    except Exception as e:
        st.error(f"Error processing audio file: {str(e)}")
        logger.error(f"S3 audio processing error: {str(e)}")
        return None

def main():
    st.title("Voice Matching System")
    
    # Initialize AWS clients
    if not init_aws_clients():
        return
    
    # System prompt input
    st.header("System Prompt")
    system_prompt = st.text_area("Enter system prompt", value=st.session_state.system_prompt, height=300)
    if st.button("Update System Prompt"):
        st.session_state.system_prompt = system_prompt
        st.success("System prompt updated!")
    
    # S3 URI input
    st.header("Audio Input")
    s3_uri = st.text_input("Enter S3 URI (e.g., s3://bucket-name/path/to/audio.mp3)")
    
    if st.button("Process Audio") and s3_uri:
        with st.spinner("Processing audio file..."):
            transcript = process_s3_audio(s3_uri)
            
            if transcript:
                st.success("Audio processed successfully!")
                st.subheader("Transcript")
                st.write(transcript)
                
                # Process with Bedrock
                with st.spinner("Analyzing transcript..."):
                    response = call_bedrock(transcript, system_prompt)
                    
                    # Store response
                    st.session_state.responses.append({
                        "transcript": transcript,
                        "response": response
                    })
    
    # Display results
    st.header("Results")
    if st.session_state.responses:
        for item in reversed(st.session_state.responses):  # Show newest first
            st.write("Transcript:", item["transcript"])
            response = item["response"]
            if response.get("matched_word"):
                st.json({
                    "matched_word": response["matched_word"],
                    "match_type": response["match_type"],
                    "confidence": response["confidence"]
                })
            else:
                st.write("No match found")
            st.write("---")

if __name__ == "__main__":
    main()
