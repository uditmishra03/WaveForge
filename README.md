# WaveForge - Image Generation Application

## Architecture

<img width="961" height="480" alt="Architecture-ImageGeneration drawio" src="https://github.com/user-attachments/assets/c2d4a9d9-f220-49ef-82da-93a9decb8e68" />

### System Flow
1. **User** sends GET request with prompt parameter
2. **API Gateway** receives and forwards request to Lambda
3. **Lambda** processes prompt and calls Bedrock
4. **Amazon Bedrock** generates image using Titan model
5. **S3** stores generated image
6. **Lambda** creates pre-signed URLs and returns response

### Components
- **API Gateway**: REST endpoint for image generation requests
- **Lambda**: Core image generation logic (Python)
- **Amazon Bedrock**: Titan Image Generator v2 model
- **S3 Bucket**: `image-generation-29072025` for image storage

### Data Flow
```
GET /imagegenApi?prompt=text description
↓
Lambda Function
↓
Bedrock Titan Model
↓
Base64 Image Response
↓
S3 Upload (img-hash.png)
↓
Pre-signed URLs (1h + 24h)
↓
JSON Response to User
```

## Lambda Function Details

### Dependencies
```python
import json
import boto3
import base64
import datetime
import hashlib
```

### AWS Clients
- `bedrock-runtime`: For Titan model invocation
- `s3`: For image storage and URL generation

### Core Functionality

#### 1. Input Processing
- Receives text prompt from API Gateway event
- Extracts prompt: `input_prompt = event['prompt']`

#### 2. Bedrock Request Configuration
```python
request_body = {
    "taskType": "TEXT_IMAGE",
    "textToImageParams": {
        "text": input_prompt
    },
    "imageGenerationConfig": {
        "numberOfImages": 1,
        "quality": "standard",
        "cfgScale": 8.0,
        "height": 1024,
        "width": 1024,
        "seed": 0
    }
}
```
- **Model**: `amazon.titan-image-generator-v2:0`
- **Output**: 1024x1024 PNG images

#### 3. Image Processing
- Invokes Bedrock model with JSON request
- Extracts base64 image from response
- Decodes base64 to binary image data

#### 4. File Naming Strategy
```python
def create_short_hash(text, length=8):
    hash_object = hashlib.md5(text.encode())
    return hash_object.hexdigest()[:length]

# Generate compact filename
timestamp = datetime.datetime.now().strftime('%m%d%H%M%S')
short_hash = create_short_hash(input_prompt + timestamp, 6)
poster_name = f"img-{short_hash}.png"
```
- **Format**: `img-a1b2c3.png` (compact 14-character filename)
- **Benefits**: Shorter URLs, better user experience

#### 5. S3 Upload
```python
client_s3.put_object(
    Bucket='image-generation-29072025',
    Body=response_bedrock_finalimage,
    Key=poster_name,
    ContentType='image/png'
)
```

#### 6. Pre-signed URL Generation
- **1-hour URL**: Standard access (3600 seconds)
- **24-hour URL**: Extended access (86400 seconds)
- Both URLs use the same compact filename

### Response Format
```json
{
    "statusCode": 200,
    "body": {
        "short_url_1h": "https://s3.amazonaws.com/...",
        "short_url_24h": "https://s3.amazonaws.com/...",
        "filename": "img-a1b2c3.png",
        "short_id": "abc12345",
        "message": "Image generated with shortened filename",
        "note": "URLs are much shorter due to compact filename"
    }
}
```

## API Usage

### Request
```bash
POST /generate-image
{
    "prompt": "A beautiful sunset over mountains"
}
```

### Response
Returns JSON with two pre-signed URLs (1h and 24h expiry) and metadata.

## AWS Services Configuration

### Required IAM Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": "arn:aws:bedrock:*:*:foundation-model/amazon.titan-image-generator-v2:0"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject"
            ],
            "Resource": "arn:aws:s3:::image-generation-29072025/*"
        }
    ]
}
```

### Lambda Configuration
- **Runtime**: Python 3.11
- **Memory**: 512MB-1GB (adjust based on usage)
- **Timeout**: 60 seconds (image generation can take time)

## Key Features

### Optimized File Naming
- Short, hash-based filenames reduce URL length
- MD5 hash prevents collisions
- Timestamp ensures uniqueness

### Dual URL Strategy
- 1-hour URLs for immediate use
- 24-hour URLs for extended access
- Same image, different expiry times

### Error Handling
- Built-in boto3 error handling
- Structured JSON responses
- CloudWatch logging for debugging

## Cost Breakdown (Based on $1.18 Usage)
- **Bedrock Titan**: ~$0.04 per 1024x1024 image
- **Lambda**: Minimal compute costs
- **S3**: Storage + PUT requests
- **API Gateway**: Request-based pricing

## Deployment Requirements
1. Create S3 bucket: `image-generation-29072025`
2. Set up Lambda with proper IAM role
3. Configure API Gateway integration
4. Enable Bedrock model access in AWS region

## Monitoring
- **CloudWatch Logs**: Lambda execution logs
- **CloudWatch Metrics**: Function duration, error rates
- **S3 Metrics**: Storage usage, request patterns
