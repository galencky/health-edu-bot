#!/usr/bin/env python3
"""
Sync files from local Google Drive folder to Cloudflare R2
Compares files and uploads only new/missing ones
"""
import os
import sys
import boto3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, Tuple, List
from botocore.config import Config
from botocore.exceptions import ClientError
import mimetypes
import re
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
load_dotenv()

from utils.r2_service import R2Service

class DriveToR2Sync:
    def __init__(self):
        self.google_drive_path = r"C:\Users\galen\My Drive\2025 archive\社區醫學\MedEdBot - AI 衛教翻譯機器人\ChatbotTexts"
        self.r2_service = R2Service()
        self.stats = {
            'files_scanned': 0,
            'files_in_r2': 0,
            'files_to_upload': 0,
            'files_uploaded': 0,
            'files_failed': 0,
            'bytes_uploaded': 0
        }
        
    def get_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of file for comparison"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def scan_local_files(self) -> Dict[str, Dict]:
        """Scan all files in Google Drive folder"""
        print(f"📂 Scanning local Google Drive folder: {self.google_drive_path}")
        local_files = {}
        
        for root, dirs, files in os.walk(self.google_drive_path):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.google_drive_path)
                
                # Skip system files
                if file.startswith('.') or file.startswith('~$'):
                    continue
                
                try:
                    file_stats = os.stat(file_path)
                    local_files[relative_path] = {
                        'full_path': file_path,
                        'size': file_stats.st_size,
                        'modified': datetime.fromtimestamp(file_stats.st_mtime),
                        'hash': self.get_file_hash(file_path) if file_stats.st_size < 10*1024*1024 else None  # Hash only files < 10MB
                    }
                    self.stats['files_scanned'] += 1
                except Exception as e:
                    print(f"⚠️ Error scanning {file}: {e}")
        
        print(f"✅ Found {len(local_files)} files locally")
        return local_files
    
    def parse_filename_to_r2_key(self, local_path: str) -> str:
        """Convert local filename to R2 key format"""
        # Extract filename
        filename = os.path.basename(local_path)
        
        # Try to extract user_id and timestamp from filename
        # Pattern 1: U{user_id}-{timestamp}.txt
        pattern1 = r'^(U[a-fA-F0-9]{32})-(\d{8}_\d{6})\.(txt|html|htm|pdf|wav|mp3|m4a)$'
        match1 = re.match(pattern1, filename)
        if match1:
            user_id, timestamp, ext = match1.groups()
            if ext in ['txt', 'html', 'htm', 'pdf']:
                return f"text/{user_id}/{filename}"
            elif ext in ['wav', 'mp3', 'm4a']:
                return f"tts_audio/{user_id}/{filename}"
        
        # Pattern 2: U{user_id}-{descriptor}-{timestamp}.txt
        pattern2 = r'^(U[a-fA-F0-9]{32})-(.+)-(\d{8}_\d{6})\.(txt|html|htm|pdf|wav|mp3|m4a)$'
        match2 = re.match(pattern2, filename)
        if match2:
            user_id, descriptor, timestamp, ext = match2.groups()
            if ext in ['txt', 'html', 'htm', 'pdf']:
                return f"text/{user_id}/{filename}"
            elif ext in ['wav', 'mp3', 'm4a']:
                if 'voicemail' in descriptor.lower():
                    return f"voicemail/{user_id}/{filename}"
                else:
                    return f"tts_audio/{user_id}/{filename}"
        
        # Pattern 3: U{user_id}_{timestamp}.wav (audio files)
        pattern3 = r'^(U[a-fA-F0-9]{32})_(\d{8}_\d{6})\.(wav|mp3|m4a)$'
        match3 = re.match(pattern3, filename)
        if match3:
            user_id, timestamp, ext = match3.groups()
            return f"tts_audio/{user_id}/{filename}"
        
        # Pattern 4: Files in user_id subdirectories
        parts = local_path.replace('\\', '/').split('/')
        for i, part in enumerate(parts):
            if part.startswith('U') and len(part) == 33:  # User ID
                user_id = part
                # Determine category based on file extension and path
                ext = os.path.splitext(filename)[1].lower()
                if ext in ['.txt', '.html', '.htm', '.pdf']:
                    return f"text/{user_id}/{filename}"
                elif ext in ['.wav', '.mp3', '.m4a']:
                    if 'voicemail' in local_path.lower():
                        return f"voicemail/{user_id}/{filename}"
                    else:
                        return f"tts_audio/{user_id}/{filename}"
        
        # Default: put in text folder with original structure
        ext = os.path.splitext(filename)[1].lower()
        if ext in ['.wav', '.mp3', '.m4a']:
            return f"tts_audio/unknown/{filename}"
        else:
            return f"text/unknown/{filename}"
    
    def list_r2_files(self) -> Set[str]:
        """List all files currently in R2 bucket"""
        print("🔍 Listing files in R2 bucket...")
        r2_files = set()
        
        try:
            paginator = self.r2_service.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.r2_service.bucket_name)
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        r2_files.add(obj['Key'])
                        self.stats['files_in_r2'] += 1
            
            print(f"✅ Found {len(r2_files)} files in R2")
            return r2_files
        except Exception as e:
            print(f"❌ Error listing R2 files: {e}")
            return set()
    
    def upload_file_to_r2(self, local_path: str, r2_key: str) -> bool:
        """Upload a single file to R2"""
        try:
            # Read file
            with open(local_path, 'rb') as f:
                file_data = f.read()
            
            # Upload using R2 service
            result = self.r2_service.upload_file(file_data, r2_key)
            
            if result:
                self.stats['files_uploaded'] += 1
                self.stats['bytes_uploaded'] += len(file_data)
                return True
            else:
                self.stats['files_failed'] += 1
                return False
                
        except Exception as e:
            print(f"❌ Failed to upload {os.path.basename(local_path)}: {e}")
            self.stats['files_failed'] += 1
            return False
    
    def sync_files(self, dry_run: bool = False):
        """Main sync process"""
        print("\n🚀 Starting Google Drive to R2 sync...")
        print(f"{'DRY RUN MODE - No files will be uploaded' if dry_run else 'LIVE MODE - Files will be uploaded'}\n")
        
        # Step 1: Scan local files
        local_files = self.scan_local_files()
        
        # Step 2: List R2 files
        r2_files = self.list_r2_files()
        
        # Step 3: Compare and find files to upload
        files_to_upload = []
        
        for local_path, file_info in local_files.items():
            r2_key = self.parse_filename_to_r2_key(local_path)
            
            if r2_key not in r2_files:
                files_to_upload.append({
                    'local_path': file_info['full_path'],
                    'r2_key': r2_key,
                    'size': file_info['size']
                })
                self.stats['files_to_upload'] += 1
        
        print(f"\n📊 Sync Summary:")
        print(f"  - Files scanned locally: {self.stats['files_scanned']}")
        print(f"  - Files already in R2: {self.stats['files_in_r2']}")
        print(f"  - Files to upload: {self.stats['files_to_upload']}")
        print(f"  - Total size to upload: {sum(f['size'] for f in files_to_upload) / 1024 / 1024:.2f} MB")
        
        if not files_to_upload:
            print("\n✅ All files are already synced!")
            return
        
        # Step 4: Upload files
        if not dry_run:
            print(f"\n📤 Uploading {len(files_to_upload)} files...")
            
            for i, file_info in enumerate(files_to_upload, 1):
                local_file = os.path.basename(file_info['local_path'])
                print(f"\n[{i}/{len(files_to_upload)}] Uploading: {local_file}")
                print(f"  → R2 path: {file_info['r2_key']}")
                print(f"  → Size: {file_info['size'] / 1024:.2f} KB")
                
                success = self.upload_file_to_r2(file_info['local_path'], file_info['r2_key'])
                
                if success:
                    print(f"  ✅ Uploaded successfully")
                else:
                    print(f"  ❌ Upload failed")
        else:
            print("\n📋 Files that would be uploaded:")
            for file_info in files_to_upload[:10]:  # Show first 10
                print(f"  - {os.path.basename(file_info['local_path'])} → {file_info['r2_key']}")
            if len(files_to_upload) > 10:
                print(f"  ... and {len(files_to_upload) - 10} more files")
        
        # Final summary
        print(f"\n📈 Final Statistics:")
        print(f"  - Files uploaded: {self.stats['files_uploaded']}")
        print(f"  - Files failed: {self.stats['files_failed']}")
        print(f"  - Data uploaded: {self.stats['bytes_uploaded'] / 1024 / 1024:.2f} MB")
        
        if self.stats['files_failed'] > 0:
            print(f"\n⚠️ Warning: {self.stats['files_failed']} files failed to upload")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync Google Drive files to Cloudflare R2")
    parser.add_argument('--dry-run', action='store_true', help='Show what would be uploaded without actually uploading')
    args = parser.parse_args()
    
    # Check if local folder exists
    if not os.path.exists(r"C:\Users\galen\My Drive\2025 archive\社區醫學\MedEdBot - AI 衛教翻譯機器人\ChatbotTexts"):
        print("❌ Error: Google Drive folder not found!")
        print("Please ensure the path exists: C:\\Users\\galen\\My Drive\\2025 archive\\社區醫學\\MedEdBot - AI 衛教翻譯機器人\\ChatbotTexts")
        return
    
    try:
        syncer = DriveToR2Sync()
        syncer.sync_files(dry_run=args.dry_run)
    except Exception as e:
        print(f"\n❌ Error during sync: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()