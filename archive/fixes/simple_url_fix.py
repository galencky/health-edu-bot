#!/usr/bin/env python3
"""
Simple URL fix based on local files as ground truth
Matches files by user_id and timestamp, then updates to correct R2 URL format
"""
import os
import sys
import asyncio
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from utils.database import get_async_db_session, ChatLog, TTSLog
from sqlalchemy import select

class SimpleURLFixer:
    def __init__(self):
        self.local_path = r"C:\Users\galen\My Drive\2025 archive\社區醫學\MedEdBot - AI 衛教翻譯機器人\ChatbotTexts"
        self.r2_domain = "https://galenchen.uk"
        self.stats = {
            'local_files': 0,
            'chat_logs_updated': 0,
            'tts_logs_updated': 0,
            'unmatched': 0
        }
        
    def parse_timestamp(self, filename):
        """Extract timestamp from filename - work backwards from extension"""
        # Remove extension
        base_name = os.path.splitext(filename)[0]
        
        # Work backwards to find timestamp patterns
        # Support both YYYYMMDD_HHMMSS and YYYYMMDD-HHMMSS
        # Look for the LAST occurrence of these patterns
        matches = list(re.finditer(r'(\d{8}[_-]\d{6})', base_name))
        
        if matches:
            # Get the last match (rightmost timestamp)
            last_match = matches[-1]
            timestamp_str = last_match.group(1)
            
            # Try both formats
            for fmt in ['%Y%m%d_%H%M%S', '%Y%m%d-%H%M%S']:
                try:
                    return datetime.strptime(timestamp_str.replace('-', '_'), '%Y%m%d_%H%M%S')
                except ValueError:
                    continue
        
        return None
    
    def scan_local_files(self):
        """Scan local files and organize by user_id and type"""
        print(f"📁 Scanning local files from: {self.local_path}")
        
        files_by_user = {}
        
        # Walk through all files
        for root, dirs, files in os.walk(self.local_path):
            for filename in files:
                if filename.startswith('.') or filename.startswith('~$'):
                    continue
                
                # Extract user_id (first 33 characters starting with U)
                if filename.startswith('U') and len(filename) > 33:
                    user_id = filename[:33]
                    
                    if user_id not in files_by_user:
                        files_by_user[user_id] = {
                            'txt': [],
                            'wav': [],
                            'm4a': [],
                            'mp3': []
                        }
                    
                    # Get file info
                    timestamp = self.parse_timestamp(filename)
                    file_info = {
                        'filename': filename,
                        'path': os.path.join(root, filename),
                        'timestamp': timestamp
                    }
                    
                    # Debug: Show parsed timestamp for first few files
                    if self.stats['local_files'] < 5 and timestamp:
                        print(f"   Debug: {filename} → {timestamp.strftime('%Y%m%d_%H%M%S')}")
                    
                    # Categorize by extension
                    if filename.endswith('.txt'):
                        files_by_user[user_id]['txt'].append(file_info)
                    elif filename.endswith('.wav'):
                        files_by_user[user_id]['wav'].append(file_info)
                    elif filename.endswith('.m4a'):
                        files_by_user[user_id]['m4a'].append(file_info)
                    elif filename.endswith('.mp3'):
                        files_by_user[user_id]['mp3'].append(file_info)
                    
                    self.stats['local_files'] += 1
        
        print(f"✅ Found {self.stats['local_files']} local files")
        
        # Print summary
        total_txt = sum(len(user['txt']) for user in files_by_user.values())
        total_wav = sum(len(user['wav']) for user in files_by_user.values())
        total_m4a = sum(len(user['m4a']) for user in files_by_user.values())
        total_mp3 = sum(len(user['mp3']) for user in files_by_user.values())
        
        print(f"   - TXT files: {total_txt}")
        print(f"   - WAV files: {total_wav}")
        print(f"   - M4A files: {total_m4a}")
        print(f"   - MP3 files: {total_mp3}")
        
        return files_by_user
    
    def find_matching_file(self, db_timestamp, local_files, tolerance_seconds=120):
        """Find local file matching database timestamp"""
        for file_info in local_files:
            if file_info['timestamp']:
                diff = abs((db_timestamp - file_info['timestamp']).total_seconds())
                if diff <= tolerance_seconds:
                    return file_info
        return None
    
    def generate_r2_url(self, filename, file_type):
        """Generate correct R2 URL based on filename and type"""
        # Extract user_id (first 33 characters starting with U)
        user_id = filename[:33] if filename.startswith('U') and len(filename) > 33 else 'unknown'
        
        # Simple mapping based on file extension:
        # .txt → text directory
        # .m4a → voicemail directory
        # .wav → tts_audio directory
        # .mp3 → tts_audio directory (unless it has 'voicemail' in name)
        
        if file_type == 'txt':
            return f"{self.r2_domain}/text/{user_id}/{filename}"
        elif file_type == 'm4a':
            return f"{self.r2_domain}/voicemail/{user_id}/{filename}"
        elif file_type == 'wav':
            return f"{self.r2_domain}/tts_audio/{user_id}/{filename}"
        elif file_type == 'mp3':
            # MP3 could be either TTS or voicemail, check filename
            if 'voicemail' in filename.lower():
                return f"{self.r2_domain}/voicemail/{user_id}/{filename}"
            else:
                return f"{self.r2_domain}/tts_audio/{user_id}/{filename}"
        
        return None
    
    async def update_urls(self, dry_run=True):
        """Update database URLs based on local files"""
        print(f"\n🔧 {'[DRY RUN] ' if dry_run else ''}Updating URLs based on local files...")
        
        # Scan local files
        files_by_user = self.scan_local_files()
        
        async with get_async_db_session() as session:
            # Update chat_logs (text files)
            print("\n📊 Updating chat_logs...")
            result = await session.execute(
                select(ChatLog).where(
                    ChatLog.gemini_output_url.like('https://%')
                )
            )
            
            for log in result.scalars():
                user_files = files_by_user.get(log.user_id, {})
                if not user_files:
                    self.stats['unmatched'] += 1
                    if dry_run:
                        print(f"[NO MATCH] Chat log {log.id} - {log.user_id} - {log.timestamp} (user not found in local files)")
                    continue
                
                matched_file = self.find_matching_file(log.timestamp, user_files.get('txt', []))
                
                if matched_file:
                    new_url = self.generate_r2_url(matched_file['filename'], 'txt')
                    
                    if dry_run:
                        print(f"[DRY RUN] Chat log {log.id}:")
                        print(f"  File: {matched_file['filename']}")
                        print(f"  Old: {log.gemini_output_url}")
                        print(f"  New: {new_url}")
                    else:
                        log.gemini_output_url = new_url
                        self.stats['chat_logs_updated'] += 1
                else:
                    self.stats['unmatched'] += 1
                    if dry_run:
                        print(f"[NO MATCH] Chat log {log.id} - {log.user_id} - {log.timestamp}")
            
            # Update tts_logs (audio files)
            print("\n🔊 Updating tts_logs...")
            result = await session.execute(
                select(TTSLog).where(
                    TTSLog.drive_link.like('https://%')
                )
            )
            
            for log in result.scalars():
                user_files = files_by_user.get(log.user_id, {})
                if not user_files:
                    self.stats['unmatched'] += 1
                    if dry_run:
                        print(f"[NO MATCH] TTS log {log.id} - {log.user_id} - {log.timestamp} (user not found in local files)")
                    continue
                
                # Try to match by filename if available
                matched_file = None
                if log.audio_filename:
                    # Direct filename match
                    for file_type in ['wav', 'm4a', 'mp3']:
                        for file_info in user_files.get(file_type, []):
                            if file_info['filename'] == log.audio_filename:
                                matched_file = file_info
                                break
                        if matched_file:
                            break
                
                # If no direct match, try timestamp matching
                if not matched_file:
                    for file_type in ['wav', 'm4a', 'mp3']:
                        matched_file = self.find_matching_file(log.timestamp, user_files.get(file_type, []))
                        if matched_file:
                            break
                
                if matched_file:
                    # Determine file type from extension
                    file_type = matched_file['filename'].split('.')[-1].lower()
                    new_url = self.generate_r2_url(matched_file['filename'], file_type)
                    
                    if dry_run:
                        print(f"[DRY RUN] TTS log {log.id}:")
                        print(f"  File: {matched_file['filename']}")
                        print(f"  Old: {log.drive_link}")
                        print(f"  New: {new_url}")
                    else:
                        log.drive_link = new_url
                        self.stats['tts_logs_updated'] += 1
                else:
                    self.stats['unmatched'] += 1
                    if dry_run:
                        print(f"[NO MATCH] TTS log {log.id} - {log.user_id} - {log.audio_filename} - {log.timestamp}")
            
            if not dry_run:
                await session.commit()
                print("\n✅ Changes committed to database")
        
        # Print summary
        print(f"\n📈 Summary:")
        print(f"  Local files scanned: {self.stats['local_files']}")
        print(f"  Chat logs updated: {self.stats['chat_logs_updated']}")
        print(f"  TTS logs updated: {self.stats['tts_logs_updated']}")
        print(f"  Unmatched records: {self.stats['unmatched']}")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple URL fix based on local files")
    parser.add_argument('--live', action='store_true', help='Actually update the database')
    args = parser.parse_args()
    
    if not os.getenv("DATABASE_URL"):
        print("❌ Error: DATABASE_URL not found")
        return
    
    try:
        fixer = SimpleURLFixer()
        await fixer.update_urls(dry_run=not args.live)
        
        if not args.live and (fixer.stats['unmatched'] < fixer.stats['local_files']):
            print(f"\n💡 To apply these updates, run with --live flag")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())