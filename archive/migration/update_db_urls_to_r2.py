#!/usr/bin/env python3
"""
Update database URLs from Google Drive to Cloudflare R2
This script updates existing Google Drive URLs in the database to point to R2
"""
import os
import sys
import re
import asyncio
from datetime import datetime
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from utils.database import get_async_db_session, ChatLog, TTSLog, VoicemailLog
from sqlalchemy import select, update

class DatabaseURLMigrator:
    def __init__(self):
        # Use custom domain for R2 public URL
        self.r2_public_url = 'https://galenchen.uk'
        self.stats = {
            'chat_logs_scanned': 0,
            'chat_logs_updated': 0,
            'tts_logs_scanned': 0,
            'tts_logs_updated': 0,
            'voicemail_logs_scanned': 0,
            'voicemail_logs_updated': 0,
            'errors': 0
        }
        self.dry_run = True  # Default to dry run for safety
        
    def extract_info_from_filename(self, filename: str) -> Tuple[str, str, str]:
        """Extract user_id, timestamp, and type from filename"""
        # Remove extension
        base_name = os.path.splitext(filename)[0]
        
        # Pattern 1: U{user_id}-{timestamp}
        pattern1 = r'^(U[a-fA-F0-9]{32})-(\d{8}_\d{6})$'
        match1 = re.match(pattern1, base_name)
        if match1:
            return match1.group(1), match1.group(2), 'standard'
        
        # Pattern 2: U{user_id}-{descriptor}-{timestamp}
        pattern2 = r'^(U[a-fA-F0-9]{32})-(.+)-(\d{8}_\d{6})$'
        match2 = re.match(pattern2, base_name)
        if match2:
            return match2.group(1), match2.group(3), match2.group(2)
        
        # Pattern 3: U{user_id}_{timestamp} (audio files)
        pattern3 = r'^(U[a-fA-F0-9]{32})_(\d{8}_\d{6})$'
        match3 = re.match(pattern3, base_name)
        if match3:
            return match3.group(1), match3.group(2), 'audio'
        
        return None, None, None
    
    def google_drive_to_r2_url(self, drive_url: str, file_type: str = 'text') -> str:
        """Convert Google Drive URL to R2 URL"""
        if not drive_url or not drive_url.startswith('https://drive.google.com'):
            return drive_url
        
        # Extract file ID from Google Drive URL
        # Format: https://drive.google.com/file/d/{FILE_ID}/view?usp=drivesdk
        match = re.search(r'/file/d/([a-zA-Z0-9_-]+)/', drive_url)
        if not match:
            return drive_url
        
        # For text files (Gemini outputs), we need to construct the R2 URL
        # We'll need to look up the actual filename from the database context
        # For now, return a placeholder that indicates migration is needed
        return f"NEEDS_MIGRATION:{match.group(1)}"
    
    async def update_chat_logs(self):
        """Update gemini_output_url in chat_logs table"""
        print("\n📊 Updating chat_logs table...")
        
        async with get_async_db_session() as session:
            # Get all records with Google Drive URLs
            result = await session.execute(
                select(ChatLog).where(
                    ChatLog.gemini_output_url.like('https://drive.google.com%')
                )
            )
            records = result.scalars().all()
            
            print(f"Found {len(records)} chat logs with Google Drive URLs")
            self.stats['chat_logs_scanned'] = len(records)
            
            for record in records:
                try:
                    # Extract user_id and timestamp from the record
                    user_id = record.user_id
                    timestamp = record.timestamp.strftime('%Y%m%d_%H%M%S')
                    
                    # Construct R2 URL
                    # Format: https://galenchen.uk/text/{user_id}/{user_id}-{timestamp}.txt
                    filename = f"{user_id}-{timestamp}.txt"
                    new_url = f"{self.r2_public_url}/text/{user_id}/{filename}"
                    
                    if self.dry_run:
                        print(f"  [DRY RUN] Would update record {record.id}:")
                        print(f"    Old: {record.gemini_output_url}")
                        print(f"    New: {new_url}")
                    else:
                        record.gemini_output_url = new_url
                        await session.commit()
                        print(f"  ✅ Updated record {record.id}")
                    
                    self.stats['chat_logs_updated'] += 1
                    
                except Exception as e:
                    print(f"  ❌ Error updating record {record.id}: {e}")
                    self.stats['errors'] += 1
    
    async def update_tts_logs(self):
        """Update drive_link in tts_logs table"""
        print("\n🔊 Updating tts_logs table...")
        
        async with get_async_db_session() as session:
            # Get all records with Google Drive URLs
            result = await session.execute(
                select(TTSLog).where(
                    TTSLog.drive_link.like('https://drive.google.com%')
                )
            )
            records = result.scalars().all()
            
            print(f"Found {len(records)} TTS logs with Google Drive URLs")
            self.stats['tts_logs_scanned'] = len(records)
            
            for record in records:
                try:
                    # Use the audio_filename to construct R2 URL
                    if record.audio_filename:
                        user_id = record.user_id
                        # Format: https://galenchen.uk/tts_audio/{user_id}/{filename}
                        new_url = f"{self.r2_public_url}/tts_audio/{user_id}/{record.audio_filename}"
                        
                        if self.dry_run:
                            print(f"  [DRY RUN] Would update record {record.id}:")
                            print(f"    Old: {record.drive_link}")
                            print(f"    New: {new_url}")
                        else:
                            record.drive_link = new_url
                            await session.commit()
                            print(f"  ✅ Updated record {record.id}")
                        
                        self.stats['tts_logs_updated'] += 1
                    
                except Exception as e:
                    print(f"  ❌ Error updating record {record.id}: {e}")
                    self.stats['errors'] += 1
    
    async def update_voicemail_logs(self):
        """Update drive_link in voicemail_logs table"""
        print("\n📞 Updating voicemail_logs table...")
        
        async with get_async_db_session() as session:
            # Get all records with Google Drive URLs
            result = await session.execute(
                select(VoicemailLog).where(
                    VoicemailLog.drive_link.like('https://drive.google.com%')
                )
            )
            records = result.scalars().all()
            
            print(f"Found {len(records)} voicemail logs with Google Drive URLs")
            self.stats['voicemail_logs_scanned'] = len(records)
            
            for record in records:
                try:
                    # Use the audio_filename to construct R2 URL
                    if record.audio_filename:
                        user_id = record.user_id
                        # Format: https://galenchen.uk/voicemail/{user_id}/{filename}
                        new_url = f"{self.r2_public_url}/voicemail/{user_id}/{record.audio_filename}"
                        
                        if self.dry_run:
                            print(f"  [DRY RUN] Would update record {record.id}:")
                            print(f"    Old: {record.drive_link}")
                            print(f"    New: {new_url}")
                        else:
                            record.drive_link = new_url
                            await session.commit()
                            print(f"  ✅ Updated record {record.id}")
                        
                        self.stats['voicemail_logs_updated'] += 1
                    
                except Exception as e:
                    print(f"  ❌ Error updating record {record.id}: {e}")
                    self.stats['errors'] += 1
    
    async def create_backup_queries(self):
        """Generate SQL backup queries before migration"""
        print("\n💾 Generating backup SQL queries...")
        
        backup_file = f"db_url_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        
        with open(backup_file, 'w') as f:
            f.write("-- Backup of URLs before R2 migration\n")
            f.write(f"-- Generated on {datetime.now()}\n\n")
            
            # Backup chat_logs
            async with get_async_db_session() as session:
                result = await session.execute(
                    select(ChatLog.id, ChatLog.gemini_output_url).where(
                        ChatLog.gemini_output_url.like('https://drive.google.com%')
                    )
                )
                for row in result:
                    f.write(f"-- chat_logs id={row[0]}\n")
                    f.write(f"UPDATE chat_logs SET gemini_output_url = '{row[1]}' WHERE id = {row[0]};\n\n")
                
                # Backup tts_logs
                result = await session.execute(
                    select(TTSLog.id, TTSLog.drive_link).where(
                        TTSLog.drive_link.like('https://drive.google.com%')
                    )
                )
                for row in result:
                    f.write(f"-- tts_logs id={row[0]}\n")
                    f.write(f"UPDATE tts_logs SET drive_link = '{row[1]}' WHERE id = {row[0]};\n\n")
                
                # Backup voicemail_logs
                result = await session.execute(
                    select(VoicemailLog.id, VoicemailLog.drive_link).where(
                        VoicemailLog.drive_link.like('https://drive.google.com%')
                    )
                )
                for row in result:
                    f.write(f"-- voicemail_logs id={row[0]}\n")
                    f.write(f"UPDATE voicemail_logs SET drive_link = '{row[1]}' WHERE id = {row[0]};\n\n")
        
        print(f"✅ Backup saved to: {backup_file}")
        return backup_file
    
    async def run_migration(self, dry_run: bool = True):
        """Run the complete migration"""
        self.dry_run = dry_run
        
        print("🚀 Starting database URL migration from Google Drive to R2")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
        print("=" * 60)
        
        # Create backup first
        if not dry_run:
            backup_file = await self.create_backup_queries()
            print(f"Backup created: {backup_file}")
            print("=" * 60)
        
        # Update each table
        await self.update_chat_logs()
        await self.update_tts_logs()
        await self.update_voicemail_logs()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📈 Migration Summary:")
        print(f"  Chat logs scanned: {self.stats['chat_logs_scanned']}")
        print(f"  Chat logs updated: {self.stats['chat_logs_updated']}")
        print(f"  TTS logs scanned: {self.stats['tts_logs_scanned']}")
        print(f"  TTS logs updated: {self.stats['tts_logs_updated']}")
        print(f"  Voicemail logs scanned: {self.stats['voicemail_logs_scanned']}")
        print(f"  Voicemail logs updated: {self.stats['voicemail_logs_updated']}")
        print(f"  Total errors: {self.stats['errors']}")
        
        if dry_run:
            print("\n⚠️  This was a DRY RUN. No changes were made.")
            print("To apply changes, run with --live flag")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Update database URLs from Google Drive to Cloudflare R2")
    parser.add_argument('--live', action='store_true', help='Actually update the database (default is dry run)')
    args = parser.parse_args()
    
    # Check environment
    if not os.getenv("DATABASE_URL"):
        print("❌ Error: DATABASE_URL not found in environment variables")
        print("Please ensure your .env file is configured")
        return
    
    if not os.getenv("R2_PUBLIC_URL"):
        print("⚠️  Warning: R2_PUBLIC_URL not set, using default: https://galenchen.uk")
    
    try:
        migrator = DatabaseURLMigrator()
        await migrator.run_migration(dry_run=not args.live)
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())