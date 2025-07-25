#!/usr/bin/env python3
"""
Upload files to Cloudflare R2 with proper encoding
This is an updated version that ensures text files have correct charset
"""

import os
import sys
import csv
from pathlib import Path
import mimetypes

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import boto3
from botocore.config import Config

load_dotenv()

# Configuration
ORGANIZED_DIR = r"C:\Users\galen\Downloads\mededbot_drive_organized"
ORIGINAL_DIR = r"C:\Users\galen\Downloads\mededbot_drive"
DOWNLOAD_BASE_DIR = ORGANIZED_DIR if os.path.exists(ORGANIZED_DIR) else ORIGINAL_DIR
UPLOAD_LOG_FILE = "r2_upload_log_v2.csv"

class CloudflareR2Uploader:
    def __init__(self):
        self.r2_client = self._init_r2_client()
        self.bucket_name = os.getenv('R2_BUCKET_NAME', 'mededbot')
        self.public_url = os.getenv('R2_PUBLIC_URL', 'https://galenchen.uk')
        self.stats = {
            'total': 0,
            'uploaded': 0,
            'failed': 0,
            'skipped': 0
        }
        self.upload_log = []
        
    def _init_r2_client(self):
        """Initialize Cloudflare R2 client"""
        required_vars = ['R2_ENDPOINT_URL', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY']
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            print("ERROR: Missing R2 configuration:")
            for var in missing:
                print(f"  - {var}")
            print("\nPlease set these in .env file")
            sys.exit(1)
        
        return boto3.client(
            's3',
            endpoint_url=os.getenv('R2_ENDPOINT_URL'),
            aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
            config=Config(
                signature_version='s3v4',
                region_name='auto'
            )
        )
    
    def get_content_type(self, file_path):
        """Get content type for file with proper charset for text files"""
        content_type, _ = mimetypes.guess_type(file_path)
        
        if not content_type:
            ext = Path(file_path).suffix.lower()
            content_type_map = {
                '.wav': 'audio/wav',
                '.mp3': 'audio/mpeg',
                '.m4a': 'audio/mp4',
                '.aac': 'audio/aac',
                '.html': 'text/html; charset=utf-8',
                '.htm': 'text/html; charset=utf-8',
                '.txt': 'text/plain; charset=utf-8',
                '.pdf': 'application/pdf',
                '.json': 'application/json; charset=utf-8',
                '.xml': 'text/xml; charset=utf-8'
            }
            content_type = content_type_map.get(ext, 'application/octet-stream')
        else:
            # Add UTF-8 charset for text files
            if content_type.startswith('text/') and 'charset' not in content_type:
                content_type += '; charset=utf-8'
        
        return content_type
    
    def upload_file(self, local_path, r2_key):
        """Upload a single file to R2"""
        try:
            content_type = self.get_content_type(local_path)
            file_size = os.path.getsize(local_path)
            
            print(f"  Uploading: {os.path.basename(local_path)} ({file_size:,} bytes)")
            print(f"  R2 Key: {r2_key}")
            print(f"  Content-Type: {content_type}")
            
            # Additional headers for text files
            extra_args = {
                'ContentType': content_type
            }
            
            # Add cache control for text files
            if content_type.startswith('text/'):
                extra_args['CacheControl'] = 'no-cache'
            
            with open(local_path, 'rb') as f:
                self.r2_client.put_object(
                    Bucket=self.bucket_name,
                    Key=r2_key,
                    Body=f,
                    **extra_args
                )
            
            r2_url = f"{self.public_url}/{r2_key}"
            print(f"  ✓ Uploaded to: {r2_url}")
            
            return r2_url
            
        except Exception as e:
            print(f"  ✗ Upload failed: {str(e)}")
            return None
    
    def process_directory(self, category):
        """Process all files in a category directory"""
        category_dir = os.path.join(DOWNLOAD_BASE_DIR, category)
        if not os.path.exists(category_dir):
            print(f"Directory not found: {category_dir}")
            return
        
        print(f"\n{'='*60}")
        print(f"UPLOADING {category.upper()}")
        print(f"{'='*60}")
        
        # Walk through all user directories
        for user_dir in os.listdir(category_dir):
            user_path = os.path.join(category_dir, user_dir)
            if not os.path.isdir(user_path):
                continue
                
            print(f"\nUser: {user_dir}")
            
            # Read metadata if exists
            metadata_file = os.path.join(user_path, 'metadata.csv')
            metadata_map = {}
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        filename = row.get('filename', '')
                        if filename:
                            metadata_map[filename] = row
            
            # Process each file
            for filename in os.listdir(user_path):
                if filename in ['metadata.csv', 'desktop.ini']:
                    continue
                    
                local_path = os.path.join(user_path, filename)
                if not os.path.isfile(local_path):
                    continue
                
                self.stats['total'] += 1
                print(f"\n[{self.stats['total']}] {filename}")
                
                # Create R2 key
                r2_key = f"{category}/{user_dir}/{filename}"
                
                # Check if already uploaded
                if self._check_already_uploaded(r2_key):
                    print("  → Already uploaded")
                    self.stats['skipped'] += 1
                    continue
                
                # Upload to R2
                r2_url = self.upload_file(local_path, r2_key)
                
                if r2_url:
                    self.stats['uploaded'] += 1
                    
                    # Get metadata
                    metadata = metadata_map.get(filename, {})
                    
                    # Log the upload
                    self.upload_log.append({
                        'category': category,
                        'user_id': user_dir,
                        'filename': filename,
                        'r2_key': r2_key,
                        'r2_url': r2_url,
                        'type': metadata.get('type', ''),
                        'timestamp': metadata.get('timestamp', '')
                    })
                else:
                    self.stats['failed'] += 1
    
    def _check_already_uploaded(self, r2_key):
        """Check if file already exists in R2"""
        try:
            self.r2_client.head_object(Bucket=self.bucket_name, Key=r2_key)
            return True
        except:
            return False
    
    def save_upload_log(self):
        """Save upload log"""
        if self.upload_log:
            with open(UPLOAD_LOG_FILE, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['category', 'user_id', 'filename', 'r2_key', 'r2_url', 'type', 'timestamp']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.upload_log)
            print(f"\nUpload log saved to: {UPLOAD_LOG_FILE}")
    
    def print_summary(self):
        """Print upload summary"""
        print("\n" + "="*60)
        print("UPLOAD SUMMARY")
        print("="*60)
        print(f"Total files: {self.stats['total']}")
        print(f"Uploaded: {self.stats['uploaded']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Skipped: {self.stats['skipped']}")
        
        if self.upload_log:
            print(f"\nUpload log saved with {len(self.upload_log)} entries")


def main():
    """Main entry point"""
    print("Cloudflare R2 Upload Tool v2 (with proper encoding)")
    print("="*60)
    
    # Check if directory exists
    if not os.path.exists(DOWNLOAD_BASE_DIR):
        print(f"ERROR: Directory not found: {DOWNLOAD_BASE_DIR}")
        print("Please run sort_downloaded_files.py first")
        sys.exit(1)
    
    print(f"Using directory: {DOWNLOAD_BASE_DIR}")
    
    # Initialize uploader
    uploader = CloudflareR2Uploader()
    
    # Process each category
    categories = ['tts_audio', 'voicemail', 'text']
    for category in categories:
        uploader.process_directory(category)
    
    # Save upload log
    uploader.save_upload_log()
    
    # Print summary
    uploader.print_summary()
    
    print("\n" + "="*60)
    print("Upload complete!")
    print("\nText files are now uploaded with proper UTF-8 encoding.")
    print("They should display correctly in browsers.")


if __name__ == "__main__":
    main()