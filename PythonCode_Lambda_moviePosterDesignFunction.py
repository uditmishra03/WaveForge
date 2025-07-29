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
    # Create a much shorter filename for better URLs
    timestamp = datetime.datetime.now().strftime('%m%d%H%M%S')  # Shorter timestamp format
    short_hash = create_short_hash(input_prompt + timestamp, 6)  # 6-character hash
    poster_name = f"img-{short_hash}.png"  # Much shorter: img-a1b2c3.png

    response_s3=client_s3.put_object(
        Bucket='image-generation-29072025',
        Body=response_bedrock_finalimage,
        Key=poster_name,
        ContentType='image/png')

#8. Generate Pre-Signed URL with shorter filename
    # Generate presigned URLs with different expiry times
    generate_presigned_url = client_s3.generate_presigned_url('get_object', Params={'Bucket':'image-generation-29072025','Key':poster_name}, ExpiresIn=3600)
    extended_presigned_url = client_s3.generate_presigned_url('get_object', Params={'Bucket':'image-generation-29072025','Key':poster_name}, ExpiresIn=86400)  # 24 hours
    
    print("1 Hour URL:", generate_presigned_url)
    print("24 Hour URL:", extended_presigned_url)
    print("Short filename:", poster_name)
    
    # Generate a short ID for reference
    short_id = create_short_hash(poster_name)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'short_url_1h': generate_presigned_url,
            'short_url_24h': extended_presigned_url,
            'filename': poster_name,
            'short_id': short_id,
            'message': 'Image generated with shortened filename',
            'note': 'URLs are much shorter due to compact filename. Use 24h URL for longer access.'
        })
    }
