# Voice Matching Project

## Overview
A serverless voice generation and processing system using AWS services, designed to create and analyze audio variations across different accents and voices.

## Architecture

### Infrastructure Components
- AWS S3: File storage
- AWS Lambda: Serverless compute
- AWS Step Functions: Workflow orchestration
- Amazon Polly: Text-to-speech generation
- Amazon Transcribe: Speech-to-text conversion
- Amazon EventBridge: Event triggering

### Workflow Stages
1. **Audio Generation**
   - Input: Dictionary of words
   - Process: Generate MP3 files using Amazon Polly
   - Supports multiple voices and accents
   - Outputs: Audio files in various languages

2. **Transcription**
   - Input: Generated audio files
   - Process: Convert audio to text using Amazon Transcribe
   - Outputs: Transcription results

3. **Dictionary Processing**
   - Input: Original dictionary and transcriptions
   - Process: Generate variations dictionary
   - Outputs: Enhanced dictionary with metadata

## Deployment

### Prerequisites
- AWS Account
- AWS CLI configured
- Python 3.11
- Virtual environment tool (venv/conda)

### Prepare Lambda Layer with Project Dependencies

#### 1. Create Virtual Environment
```bash
python3.11 -m venv lambda_layer_env
source lambda_layer_env/bin/activate
```

#### 2. Install Project Dependencies
```bash
# Install project dependencies
pip install \
    boto3 \
    botocore \
    numpy \
    pandas \
    phonetics

# Create requirements file
pip freeze > requirements.txt
```

#### 3. Prepare Lambda Layer Structure
```bash
# Create layer directory structure
mkdir -p lambda_layer/python/offline

# Install dependencies
pip install -r requirements.txt -t lambda_layer/python

# Copy Python scripts to offline package
cp py/*.py lambda_layer/python/offline/
touch lambda_layer/python/offline/__init__.py
```

#### 4. Create Lambda Layer ZIP
```bash
# Compress layer
cd lambda_layer
zip -r ../lambda_layer.zip python/
cd ..
```

#### 5. Upload Lambda Layer to S3
```bash
# Replace with your S3 bucket name
aws s3 cp lambda_layer.zip s3://voice-matching-zytest/lambda_layer.zip
```

### Project Scripts Included in Layer
- `polly_audio_generator.py`
- `transcribe_audio.py`
- `generate_variations_dict.py`
- `word_matcher.py`

### Deploy CloudFormation Stack
```bash
aws cloudformation create-stack
--stack-name voice-matching-project-1
--template-body file://full_stack.yaml
--capabilities CAPABILITY_IAM
--parameters
ParameterKey=ProjectName,ParameterValue=VoiceMatchingProject
ParameterKey=ExistingS3BucketName,ParameterValue=voice-matching-zytest
ParameterKey=PythonRuntimeVersion,ParameterValue=python3.10
ParameterKey=InputPrefix,ParameterValue=input/
ParameterKey=GeneratedAudioPrefix,ParameterValue=generated_audio/
ParameterKey=TranscriptionPrefix,ParameterValue=transcriptions/
ParameterKey=ProcessedDictPrefix,ParameterValue=processed_dict/
```

### S3 event notication
Please ensure your target s3 eventbrigde notification was configured to **on**

## Configuration

### Environment Variables
- `INPUT_BUCKET`: S3 bucket for input files
- `INPUT_PREFIX`: S3 prefix for input files
- `OUTPUT_BUCKET`: S3 bucket for output files
- `OUTPUT_PREFIX`: S3 prefix for output files

### Customization
- Modify `voice_matching_cloudformation.yaml` to:
  - Change voice configurations
  - Adjust Lambda function resources
  - Update S3 bucket settings

## Error Handling
- Retry mechanisms in Step Function
- Comprehensive error logging
- Maximum workflow timeout: 1 hour

## Monitoring
- CloudWatch logs for Lambda functions
- Step Function execution tracking
- S3 event notifications

## Security
- IAM roles with least-privilege access
- S3 bucket public access blocked
- Encryption at rest and in transit

## Scalability
- Serverless architecture
- Parallel processing in transcription stage
- Configurable Lambda function resources

## Troubleshooting

### Common Issues
1. **Lambda Layer Dependency Conflicts**
   - Ensure all dependencies are compatible
   - Use `pip freeze` to lock versions
   - Test layer independently

2. **S3 Bucket Configuration**
   - Verify bucket name and region
   - Check IAM permissions
   - Ensure public access is blocked

3. **Step Function Execution**
   - Review CloudWatch logs
   - Check Lambda function error messages
   - Validate input data format

## Contributing
1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create pull request

## License
[Specify your license here]

## Contact
[Your contact information]
# voice_matching_offline
