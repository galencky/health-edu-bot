#!/usr/bin/env python3
"""
Step 1: Download all files from Google Drive based on database records
This script downloads files and organizes them locally for inspection before uploading to R2
"""

import os
import sys
import asyncio
import csv
import json
import base64
import tempfile
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
import io

from utils.database import get_async_db_session, ChatLog, TTSLog, VoicemailLog
from sqlalchemy import select, and_

load_dotenv()

# Configuration
DOWNLOAD_BASE_DIR = r"C:\Users\galen\Downloads\mededbot_drive"
BATCH_SIZE = 10  # Download in batches to avoid overwhelming

class GoogleDriveDownloader:
    def __init__(self):
        self.drive_service = self._init_google_drive()
        self.stats = {
            'total': 0,
            'downloaded': 0,
            'failed': 0,
            'skipped': 0
        }
        self.failed_downloads = []
        
    def _init_google_drive(self):
        """Initialize Google Drive service"""
        # First try base64 encoded credentials
        google_creds_b64 = os.getenv('GOOGLE_CREDS_B64')
        if google_creds_b64:
            try:
                # Decode base64 credentials
                creds_json = base64.b64decode(google_creds_b64).decode('utf-8')
                creds_dict = json.loads(creds_json)
                
                # Create credentials from the decoded JSON
                credentials = service_account.Credentials.from_service_account_info(
                    creds_dict,
                    scopes=['https://www.googleapis.com/auth/drive.readonly']
                )
                
                print("✓ Using base64-encoded Google credentials")
                return build('drive', 'v3', credentials=credentials)
                
            except Exception as e:
                print(f"ERROR: Failed to decode GOOGLE_CREDS_B64: {e}")
                print("Falling back to service account file...")
        
        # Fall back to service account file
        service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
        if service_account_file and os.path.exists(service_account_file):
            credentials = service_account.Credentials.from_service_account_file(
                service_account_file,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            print("✓ Using Google service account file")
            return build('drive', 'v3', credentials=credentials)
        else:
            print("ERROR: No Google credentials found!")
            print("Please set either:")
            print("  - GOOGLE_CREDS_B64 (base64-encoded credentials)")
            print("  - GOOGLE_SERVICE_ACCOUNT_FILE (path to JSON file)")
            sys.exit(1)
    
    def extract_file_id(self, drive_url):
        """Extract file ID from Google Drive URL"""
        if not drive_url:
            return None
            
        try:
            if '/file/d/' in drive_url:
                parts = drive_url.split('/file/d/')
                if len(parts) > 1:
                    file_id = parts[1].split('/')[0]
                    return file_id
            elif 'id=' in drive_url:
                parsed = urlparse(drive_url)
                params = parse_qs(parsed.query)
                if 'id' in params:
                    return params['id'][0]
        except:
            pass
            
        return None
    
    def download_file(self, file_id, output_path):
        """Download a single file from Google Drive"""
        try:
            # Get file metadata
            file_metadata = self.drive_service.files().get(
                fileId=file_id,
                fields='name,mimeType,size'
            ).execute()
            
            original_name = file_metadata.get('name', '')
            file_size = int(file_metadata.get('size', 0))
            print(f"  Downloading: {original_name} ({file_size:,} bytes)")
            
            # Create directory if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Download file
            request = self.drive_service.files().get_media(fileId=file_id)
            fh = io.FileIO(output_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    print(f"  Progress: {int(status.progress() * 100)}%", end='\r')
            
            fh.close()
            print(f"  ✓ Downloaded to: {output_path}")
            return True, original_name
            
        except Exception as e:
            print(f"  ✗ Failed: {str(e)}")
            return False, None
    
    async def process_chat_logs(self):
        """Download files from chat logs"""
        print("\n" + "="*60)
        print("PROCESSING CHAT LOGS")
        print("="*60)
        
        async with get_async_db_session() as session:
            result = await session.execute(
                select(ChatLog).where(
                    and_(
                        ChatLog.gemini_output_url.isnot(None),
                        ChatLog.gemini_output_url.like('%drive.google.com%')
                    )
                )
            )
            records = result.scalars().all()
            
            print(f"Found {len(records)} chat logs with Google Drive links")
            
            for i, record in enumerate(records):
                print(f"\n[{i+1}/{len(records)}] Chat Log ID: {record.id}")
                self.stats['total'] += 1
                
                file_id = self.extract_file_id(record.gemini_output_url)
                if not file_id:
                    print("  ✗ Invalid URL")
                    self.stats['skipped'] += 1
                    continue
                
                # Create organized path
                timestamp = record.timestamp.strftime('%Y%m%d_%H%M%S')
                output_dir = os.path.join(DOWNLOAD_BASE_DIR, 'chat_logs', record.user_id)
                output_filename = f"{timestamp}_gemini_output_{record.id}.html"
                output_path = os.path.join(output_dir, output_filename)
                
                # Skip if already downloaded
                if os.path.exists(output_path):
                    print(f"  → Already downloaded: {output_path}")
                    self.stats['skipped'] += 1
                    continue
                
                # Download
                success, original_name = self.download_file(file_id, output_path)
                if success:
                    self.stats['downloaded'] += 1
                    
                    # Save metadata
                    self._save_metadata(output_dir, {
                        'type': 'chat_log',
                        'db_id': record.id,
                        'user_id': record.user_id,
                        'timestamp': str(record.timestamp),
                        'original_url': record.gemini_output_url,
                        'file_id': file_id,
                        'local_path': output_path,
                        'original_filename': original_name or output_filename
                    })
                else:
                    self.stats['failed'] += 1
                    self.failed_downloads.append({
                        'type': 'chat_log',
                        'id': record.id,
                        'url': record.gemini_output_url
                    })
    
    async def process_tts_logs(self):
        """Download files from TTS logs"""
        print("\n" + "="*60)
        print("PROCESSING TTS LOGS")
        print("="*60)
        
        async with get_async_db_session() as session:
            result = await session.execute(
                select(TTSLog).where(
                    and_(
                        TTSLog.drive_link.isnot(None),
                        TTSLog.drive_link.like('%drive.google.com%')
                    )
                )
            )
            records = result.scalars().all()
            
            print(f"Found {len(records)} TTS logs with Google Drive links")
            
            for i, record in enumerate(records):
                print(f"\n[{i+1}/{len(records)}] TTS Log ID: {record.id}")
                self.stats['total'] += 1
                
                file_id = self.extract_file_id(record.drive_link)
                if not file_id:
                    print("  ✗ Invalid URL")
                    self.stats['skipped'] += 1
                    continue
                
                # Create organized path
                timestamp = record.timestamp.strftime('%Y%m%d_%H%M%S')
                output_dir = os.path.join(DOWNLOAD_BASE_DIR, 'tts_audio', record.user_id)
                
                # First try to download to get the actual filename
                temp_filename = f"temp_{record.id}_{file_id}"
                temp_path = os.path.join(output_dir, temp_filename)
                
                # Download
                success, original_name = self.download_file(file_id, temp_path)
                if success:
                    # Determine final filename
                    if original_name:
                        # Use original name from Drive, but ensure it's safe
                        safe_original = "".join(c for c in original_name if c.isalnum() or c in '._-')
                        output_filename = safe_original
                    elif record.audio_filename:
                        output_filename = record.audio_filename
                    else:
                        output_filename = f"{timestamp}_tts_{record.id}.wav"
                    
                    # Add timestamp prefix if not already present
                    if not output_filename.startswith(record.user_id):
                        output_filename = f"{timestamp}_{output_filename}"
                    
                    output_path = os.path.join(output_dir, output_filename)
                    
                    # Check if target already exists
                    if os.path.exists(output_path):
                        os.remove(temp_path)
                        print(f"  → Already exists with proper name: {output_filename}")
                        self.stats['skipped'] += 1
                        continue
                    
                    # Rename temp file to final name
                    os.rename(temp_path, output_path)
                    self.stats['downloaded'] += 1
                    
                    # Save metadata
                    self._save_metadata(output_dir, {
                        'type': 'tts_log',
                        'db_id': record.id,
                        'user_id': record.user_id,
                        'timestamp': str(record.timestamp),
                        'original_url': record.drive_link,
                        'file_id': file_id,
                        'local_path': output_path,
                        'original_filename': original_name,
                        'db_filename': record.audio_filename,
                        'text': record.text[:100] + '...' if record.text else None
                    })
                else:
                    self.stats['failed'] += 1
                    self.failed_downloads.append({
                        'type': 'tts_log',
                        'id': record.id,
                        'url': record.drive_link
                    })
    
    async def process_voicemail_logs(self):
        """Download files from voicemail logs"""
        print("\n" + "="*60)
        print("PROCESSING VOICEMAIL LOGS")
        print("="*60)
        
        async with get_async_db_session() as session:
            result = await session.execute(
                select(VoicemailLog).where(
                    and_(
                        VoicemailLog.drive_link.isnot(None),
                        VoicemailLog.drive_link.like('%drive.google.com%')
                    )
                )
            )
            records = result.scalars().all()
            
            print(f"Found {len(records)} voicemail logs with Google Drive links")
            
            for i, record in enumerate(records):
                print(f"\n[{i+1}/{len(records)}] Voicemail Log ID: {record.id}")
                self.stats['total'] += 1
                
                file_id = self.extract_file_id(record.drive_link)
                if not file_id:
                    print("  ✗ Invalid URL")
                    self.stats['skipped'] += 1
                    continue
                
                # Create organized path
                timestamp = record.timestamp.strftime('%Y%m%d_%H%M%S')
                output_dir = os.path.join(DOWNLOAD_BASE_DIR, 'voicemail', record.user_id)
                
                # First try to download to get the actual filename
                temp_filename = f"temp_{record.id}_{file_id}"
                temp_path = os.path.join(output_dir, temp_filename)
                
                # Download
                success, original_name = self.download_file(file_id, temp_path)
                if success:
                    # Determine final filename
                    if original_name:
                        # Use original name from Drive
                        safe_original = "".join(c for c in original_name if c.isalnum() or c in '._-')
                        output_filename = safe_original
                    elif record.audio_filename:
                        output_filename = record.audio_filename
                    else:
                        output_filename = f"{timestamp}_voicemail_{record.id}.m4a"
                    
                    # Add timestamp prefix if not already present
                    if not output_filename.startswith(record.user_id):
                        output_filename = f"{timestamp}_{output_filename}"
                    
                    output_path = os.path.join(output_dir, output_filename)
                    
                    # Check if target already exists
                    if os.path.exists(output_path):
                        os.remove(temp_path)
                        print(f"  → Already exists with proper name: {output_filename}")
                        self.stats['skipped'] += 1
                        continue
                    
                    # Rename temp file to final name
                    os.rename(temp_path, output_path)
                    self.stats['downloaded'] += 1
                    
                    # Save metadata
                    self._save_metadata(output_dir, {
                        'type': 'voicemail_log',
                        'db_id': record.id,
                        'user_id': record.user_id,
                        'timestamp': str(record.timestamp),
                        'original_url': record.drive_link,
                        'file_id': file_id,
                        'local_path': output_path,
                        'original_filename': original_name,
                        'db_filename': record.audio_filename,
                        'transcription': record.transcription[:100] + '...' if record.transcription else None
                    })
                else:
                    self.stats['failed'] += 1
                    self.failed_downloads.append({
                        'type': 'voicemail_log',
                        'id': record.id,
                        'url': record.drive_link
                    })
    
    def _save_metadata(self, directory, metadata):
        """Save metadata for each downloaded file"""
        metadata_file = os.path.join(directory, 'metadata.csv')
        file_exists = os.path.exists(metadata_file)
        
        with open(metadata_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=metadata.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(metadata)
    
    def save_failed_downloads(self):
        """Save list of failed downloads"""
        if self.failed_downloads:
            with open(os.path.join(DOWNLOAD_BASE_DIR, 'failed_downloads.csv'), 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['type', 'id', 'url'])
                writer.writeheader()
                writer.writerows(self.failed_downloads)
    
    def print_summary(self):
        """Print download summary"""
        print("\n" + "="*60)
        print("DOWNLOAD SUMMARY")
        print("="*60)
        print(f"Total files: {self.stats['total']}")
        print(f"Downloaded: {self.stats['downloaded']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Skipped: {self.stats['skipped']}")
        print(f"\nFiles saved to: {os.path.abspath(DOWNLOAD_BASE_DIR)}")
        
        if self.failed_downloads:
            print(f"\nFailed downloads saved to: {os.path.join(DOWNLOAD_BASE_DIR, 'failed_downloads.csv')}")
        
        # Show directory structure
        print("\nDirectory structure:")
        for root, dirs, files in os.walk(DOWNLOAD_BASE_DIR):
            level = root.replace(DOWNLOAD_BASE_DIR, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files[:3]:  # Show first 3 files
                print(f"{subindent}{file}")
            if len(files) > 3:
                print(f"{subindent}... and {len(files)-3} more files")


async def main():
    """Main entry point"""
    print("Google Drive Download Tool")
    print("="*60)
    
    # Check for Google credentials
    if not os.getenv('GOOGLE_CREDS_B64') and not os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE'):
        print("ERROR: No Google credentials found!")
        print("Please set one of the following in .env:")
        print("  - GOOGLE_CREDS_B64 (base64-encoded credentials)")
        print("  - GOOGLE_SERVICE_ACCOUNT_FILE (path to JSON file)")
        sys.exit(1)
    
    # Create download directory
    os.makedirs(DOWNLOAD_BASE_DIR, exist_ok=True)
    print(f"Download directory: {DOWNLOAD_BASE_DIR}")
    
    # Initialize downloader
    downloader = GoogleDriveDownloader()
    
    # Process each type
    await downloader.process_chat_logs()
    await downloader.process_tts_logs()
    await downloader.process_voicemail_logs()
    
    # Save failed downloads
    downloader.save_failed_downloads()
    
    # Print summary
    downloader.print_summary()


if __name__ == "__main__":
    asyncio.run(main())