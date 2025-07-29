import json
#1. import boto3
import boto3
import base64
import datetime
import hashlib

#2. Create client connection with Bedrock and S3 Services – Link
client_bedrock = boto3.client('bedrock-runtime')
client_s3 = boto3.client('s3')

def create_short_hash(text, length=8):
    """Generate a short hash from text for URL shortening"""
    hash_object = hashlib.md5(text.encode())
    return hash_object.hexdigest()[:length]

def lambda_handler(event, context):
    
#3. Store the input data (prompt) in a variable
    input_prompt=event['prompt']
    print(input_prompt)

#4. Create a Request Syntax to access the Bedrock Service (Amazon Titan Image Generator)
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
    
    response_bedrock = client_bedrock.invoke_model(
        contentType='application/json', 
        accept='application/json',
        modelId='amazon.titan-image-generator-v2:0',
        body=json.dumps(request_body)
    )
    #print(response_bedrock)   
       
#5. 5a. Retrieve from Dictionary, 5b. Convert Streaming Body to Byte using json load 5c. Print

    response_bedrock_byte=json.loads(response_bedrock['body'].read())
    print(response_bedrock_byte)
#6. 6a. Retrieve data with images key, 6b. Import Base 64, 6c. Decode from Base64
    response_bedrock_base64 = response_bedrock_byte['images'][0]
    response_bedrock_finalimage = base64.b64decode(response_bedrock_base64)
    print(response_bedrock_finalimage)
    
#7. 7a. Upload the File to S3 using Put Object Method – Link 7b. Import datetime 7c. Generate the image name to be stored in S3 - Link
    poster_name = 'image-name-'+ datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S')+'.png'

    response_s3=client_s3.put_object(
        Bucket='image-generation-29072025',
        Body=response_bedrock_finalimage,
        Key=poster_name)

#8. Generate Pre-Signed URL and Create Short URL
    generate_presigned_url = client_s3.generate_presigned_url('get_object', Params={'Bucket':'image-generation-29072025','Key':poster_name}, ExpiresIn=3600)
    print("Original URL:", generate_presigned_url)
    
    # Generate a short hash for the URL based on the poster name
    short_id = create_short_hash(poster_name)
    
    # Option 1: Make the S3 object publicly accessible and use direct URL
    try:
        # Set the object to be publicly readable
        client_s3.put_object_acl(
            Bucket='image-generation-29072025',
            Key=poster_name,
            ACL='public-read'
        )
        
        # Create a direct S3 URL (now publicly accessible)
        direct_s3_url = f"https://image-generation-29072025.s3.amazonaws.com/{poster_name}"
        public_url_available = True
        print("Public S3 URL:", direct_s3_url)
        
    except Exception as e:
        print(f"Could not make object public: {str(e)}")
        direct_s3_url = "Not available - bucket not configured for public access"
        public_url_available = False
    
    # Option 2: Create a shorter presigned URL with custom expiry
    short_presigned_url = client_s3.generate_presigned_url(
        'get_object', 
        Params={'Bucket':'image-generation-29072025','Key':poster_name}, 
        ExpiresIn=86400  # 24 hours instead of 1 hour
    )
    
    print("Short ID:", short_id)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'presigned_url': generate_presigned_url,
            'extended_presigned_url': short_presigned_url,
            'direct_s3_url': direct_s3_url if public_url_available else None,
            'short_id': short_id,
            'image_key': poster_name,
            'message': 'Image generated successfully',
            'note': 'Use direct_s3_url if available, otherwise use presigned_url for secure access',
            'url_options': {
                'public_access': public_url_available,
                'recommended_url': direct_s3_url if public_url_available else short_presigned_url
            }
        })
    }
