#!/usr/bin/env python3
"""
Fix encoding for text files already uploaded to R2
This updates the Content-Type header to include charset=utf-8
"""

import os
import sys
from dotenv import load_dotenv
import boto3
from botocore.config import Config

load_dotenv()

def fix_text_encoding():
    """Update Content-Type for text files in R2"""
    
    # Initialize R2 client
    client = boto3.client(
        's3',
        endpoint_url=os.getenv('R2_ENDPOINT_URL'),
        aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
        config=Config(
            signature_version='s3v4',
            region_name='auto'
        )
    )
    
    bucket = os.getenv('R2_BUCKET_NAME', 'mededbot')
    
    print(f"Fixing encoding for text files in bucket: {bucket}")
    print("="*60)
    
    # List all objects
    paginator = client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket)
    
    fixed_count = 0
    error_count = 0
    
    for page in pages:
        if 'Contents' not in page:
            continue
            
        for obj in page['Contents']:
            key = obj['Key']
            
            # Only process text files
            if not (key.endswith('.txt') or key.endswith('.html') or key.endswith('.htm')):
                continue
            
            try:
                # Get current metadata
                response = client.head_object(Bucket=bucket, Key=key)
                current_content_type = response.get('ContentType', '')
                
                # Skip if already has charset
                if 'charset' in current_content_type:
                    print(f"✓ Already has charset: {key}")
                    continue
                
                # Determine new content type
                if key.endswith('.html') or key.endswith('.htm'):
                    new_content_type = 'text/html; charset=utf-8'
                else:
                    new_content_type = 'text/plain; charset=utf-8'
                
                print(f"Fixing: {key}")
                print(f"  Old: {current_content_type}")
                print(f"  New: {new_content_type}")
                
                # Copy object to itself with new metadata
                client.copy_object(
                    Bucket=bucket,
                    Key=key,
                    CopySource={'Bucket': bucket, 'Key': key},
                    MetadataDirective='REPLACE',
                    ContentType=new_content_type,
                    # Preserve other metadata if needed
                    CacheControl='no-cache'
                )
                
                fixed_count += 1
                print(f"  ✓ Fixed!")
                
            except Exception as e:
                error_count += 1
                print(f"  ✗ Error: {e}")
    
    print("\n" + "="*60)
    print(f"Summary:")
    print(f"  Fixed: {fixed_count} files")
    print(f"  Errors: {error_count} files")
    print("\nDone!")

def main():
    """Main entry point"""
    # Check credentials
    required = ['R2_ENDPOINT_URL', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY']
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)
    
    print("This will update Content-Type headers for all text files in R2")
    response = input("Continue? (y/n): ")
    
    if response.lower() == 'y':
        fix_text_encoding()
    else:
        print("Aborted.")

if __name__ == "__main__":
    main()