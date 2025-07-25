#!/usr/bin/env python3
"""
Test Cloudflare R2 connection and credentials
"""

import os
import sys
from dotenv import load_dotenv
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

load_dotenv()

def test_r2_connection():
    """Test R2 connection with provided credentials"""
    print("Testing Cloudflare R2 Connection")
    print("="*60)
    
    # Check required environment variables
    required_vars = {
        'R2_ENDPOINT_URL': 'https://7c14fdde93c85ff60383f8ba066ddcf6.r2.cloudflarestorage.com',
        'R2_ACCESS_KEY_ID': None,
        'R2_SECRET_ACCESS_KEY': None,
        'R2_BUCKET_NAME': 'mededbot',
        'R2_PUBLIC_URL': None  # This is for public access to files
    }
    
    print("Checking environment variables...")
    missing = []
    for var, default in required_vars.items():
        value = os.getenv(var, default)
        if value:
            if 'SECRET' in var:
                print(f"✓ {var}: {'*' * 8}")
            else:
                print(f"✓ {var}: {value}")
        else:
            print(f"✗ {var}: NOT SET")
            missing.append(var)
    
    if missing:
        print(f"\nMissing required variables: {', '.join(missing)}")
        print("\nPlease add these to your .env file:")
        print("```")
        print("# Cloudflare R2 Configuration")
        print("R2_ENDPOINT_URL=https://7c14fdde93c85ff60383f8ba066ddcf6.r2.cloudflarestorage.com")
        print("R2_ACCESS_KEY_ID=your-access-key-here")
        print("R2_SECRET_ACCESS_KEY=your-secret-key-here")
        print("R2_BUCKET_NAME=mededbot")
        print("R2_PUBLIC_URL=https://your-public-r2-domain.com  # or https://pub-xxx.r2.dev")
        print("```")
        print("\nTo get these credentials:")
        print("1. Go to Cloudflare Dashboard > R2")
        print("2. Click on your bucket 'mededbot'")
        print("3. Go to Settings > API tokens")
        print("4. Create a new API token with read/write permissions")
        return False
    
    # Try to connect
    print("\nTesting connection...")
    try:
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
        
        # Test listing buckets
        print("Listing buckets...")
        response = client.list_buckets()
        buckets = [b['Name'] for b in response.get('Buckets', [])]
        print(f"Found buckets: {buckets}")
        
        bucket_name = os.getenv('R2_BUCKET_NAME')
        if bucket_name in buckets:
            print(f"✓ Bucket '{bucket_name}' exists")
            
            # Test listing objects
            print(f"\nListing objects in '{bucket_name}'...")
            response = client.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
            objects = response.get('Contents', [])
            if objects:
                print(f"Found {response.get('KeyCount', 0)} objects. First few:")
                for obj in objects[:5]:
                    print(f"  - {obj['Key']} ({obj['Size']} bytes)")
            else:
                print("Bucket is empty")
            
            # Test upload capability
            print("\nTesting upload capability...")
            test_key = "test/connection_test.txt"
            test_content = f"R2 connection test at {os.environ.get('COMPUTERNAME', 'unknown')}"
            
            try:
                client.put_object(
                    Bucket=bucket_name,
                    Key=test_key,
                    Body=test_content.encode('utf-8'),
                    ContentType='text/plain'
                )
                print(f"✓ Successfully uploaded test file: {test_key}")
                
                # Try to delete it
                client.delete_object(Bucket=bucket_name, Key=test_key)
                print(f"✓ Successfully deleted test file")
                
                print("\n✅ R2 connection test PASSED!")
                return True
                
            except ClientError as e:
                print(f"✗ Upload test failed: {e}")
                return False
        else:
            print(f"✗ Bucket '{bucket_name}' not found")
            print(f"Available buckets: {buckets}")
            return False
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"\n✗ Connection failed: {error_code}")
        print(f"Details: {e}")
        
        if error_code == 'InvalidAccessKeyId':
            print("\nThe Access Key ID is invalid. Please check your credentials.")
        elif error_code == 'SignatureDoesNotMatch':
            print("\nThe Secret Access Key is invalid. Please check your credentials.")
        elif error_code == 'AccessDenied':
            print("\nAccess denied. Check that your API token has the correct permissions.")
        
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False

def main():
    """Main entry point"""
    success = test_r2_connection()
    
    if success:
        print("\nYou're ready to run the upload script!")
        print("Next step: python scripts/step2_upload_to_r2.py")
    else:
        print("\nPlease fix the issues above before proceeding.")
        sys.exit(1)

if __name__ == "__main__":
    main()