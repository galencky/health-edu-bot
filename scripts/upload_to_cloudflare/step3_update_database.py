#!/usr/bin/env python3
"""
Step 3: Update database with new Cloudflare R2 URLs
This script updates the database records with the new R2 URLs from the upload log
"""

import os
import sys
import csv
import asyncio
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from sqlalchemy import select
from utils.database import get_async_db_session, ChatLog, TTSLog, VoicemailLog

load_dotenv()

# Configuration
UPLOAD_LOG_FILE = "r2_upload_log.csv"
UPDATE_LOG_FILE = f"database_update_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

class DatabaseUpdater:
    def __init__(self):
        self.stats = {
            'total': 0,
            'updated': 0,
            'failed': 0,
            'not_found': 0
        }
        self.update_log = []
        
    async def update_records(self):
        """Update database records from upload log"""
        # Read upload log
        if not os.path.exists(UPLOAD_LOG_FILE):
            print(f"ERROR: Upload log not found: {UPLOAD_LOG_FILE}")
            print("Please run step2_upload_to_r2.py first")
            sys.exit(1)
        
        uploads = []
        with open(UPLOAD_LOG_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            uploads = list(reader)
        
        print(f"Found {len(uploads)} uploaded files to process")
        
        # Group by type for batch processing
        chat_updates = [u for u in uploads if u['db_type'] == 'chat_log']
        tts_updates = [u for u in uploads if u['db_type'] == 'tts_log']
        voicemail_updates = [u for u in uploads if u['db_type'] == 'voicemail_log']
        
        # Update each type
        await self._update_chat_logs(chat_updates)
        await self._update_tts_logs(tts_updates)
        await self._update_voicemail_logs(voicemail_updates)
    
    async def _update_chat_logs(self, updates):
        """Update chat log records"""
        if not updates:
            return
            
        print(f"\n{'='*60}")
        print(f"UPDATING CHAT LOGS ({len(updates)} records)")
        print(f"{'='*60}")
        
        async with get_async_db_session() as session:
            for update in updates:
                self.stats['total'] += 1
                db_id = int(update['db_id'])
                
                print(f"\n[{self.stats['total']}] Chat Log ID: {db_id}")
                
                try:
                    # Find record
                    result = await session.execute(
                        select(ChatLog).where(ChatLog.id == db_id)
                    )
                    record = result.scalar_one_or_none()
                    
                    if not record:
                        print(f"  ✗ Record not found")
                        self.stats['not_found'] += 1
                        continue
                    
                    # Update URL
                    old_url = record.gemini_output_url
                    record.gemini_output_url = update['r2_url']
                    
                    await session.commit()
                    
                    print(f"  ✓ Updated successfully")
                    print(f"    Old: {old_url}")
                    print(f"    New: {update['r2_url']}")
                    
                    self.stats['updated'] += 1
                    self.update_log.append({
                        'type': 'chat_log',
                        'id': db_id,
                        'old_url': old_url,
                        'new_url': update['r2_url'],
                        'status': 'success'
                    })
                    
                except Exception as e:
                    print(f"  ✗ Update failed: {str(e)}")
                    self.stats['failed'] += 1
                    self.update_log.append({
                        'type': 'chat_log',
                        'id': db_id,
                        'old_url': update['original_drive_url'],
                        'new_url': update['r2_url'],
                        'status': f'failed: {str(e)}'
                    })
    
    async def _update_tts_logs(self, updates):
        """Update TTS log records"""
        if not updates:
            return
            
        print(f"\n{'='*60}")
        print(f"UPDATING TTS LOGS ({len(updates)} records)")
        print(f"{'='*60}")
        
        async with get_async_db_session() as session:
            for update in updates:
                self.stats['total'] += 1
                db_id = int(update['db_id'])
                
                print(f"\n[{self.stats['total']}] TTS Log ID: {db_id}")
                
                try:
                    # Find record
                    result = await session.execute(
                        select(TTSLog).where(TTSLog.id == db_id)
                    )
                    record = result.scalar_one_or_none()
                    
                    if not record:
                        print(f"  ✗ Record not found")
                        self.stats['not_found'] += 1
                        continue
                    
                    # Update URL
                    old_url = record.drive_link
                    record.drive_link = update['r2_url']
                    
                    await session.commit()
                    
                    print(f"  ✓ Updated successfully")
                    print(f"    Old: {old_url}")
                    print(f"    New: {update['r2_url']}")
                    
                    self.stats['updated'] += 1
                    self.update_log.append({
                        'type': 'tts_log',
                        'id': db_id,
                        'old_url': old_url,
                        'new_url': update['r2_url'],
                        'status': 'success'
                    })
                    
                except Exception as e:
                    print(f"  ✗ Update failed: {str(e)}")
                    self.stats['failed'] += 1
                    self.update_log.append({
                        'type': 'tts_log',
                        'id': db_id,
                        'old_url': update['original_drive_url'],
                        'new_url': update['r2_url'],
                        'status': f'failed: {str(e)}'
                    })
    
    async def _update_voicemail_logs(self, updates):
        """Update voicemail log records"""
        if not updates:
            return
            
        print(f"\n{'='*60}")
        print(f"UPDATING VOICEMAIL LOGS ({len(updates)} records)")
        print(f"{'='*60}")
        
        async with get_async_db_session() as session:
            for update in updates:
                self.stats['total'] += 1
                db_id = int(update['db_id'])
                
                print(f"\n[{self.stats['total']}] Voicemail Log ID: {db_id}")
                
                try:
                    # Find record
                    result = await session.execute(
                        select(VoicemailLog).where(VoicemailLog.id == db_id)
                    )
                    record = result.scalar_one_or_none()
                    
                    if not record:
                        print(f"  ✗ Record not found")
                        self.stats['not_found'] += 1
                        continue
                    
                    # Update URL
                    old_url = record.drive_link
                    record.drive_link = update['r2_url']
                    
                    await session.commit()
                    
                    print(f"  ✓ Updated successfully")
                    print(f"    Old: {old_url}")
                    print(f"    New: {update['r2_url']}")
                    
                    self.stats['updated'] += 1
                    self.update_log.append({
                        'type': 'voicemail_log',
                        'id': db_id,
                        'old_url': old_url,
                        'new_url': update['r2_url'],
                        'status': 'success'
                    })
                    
                except Exception as e:
                    print(f"  ✗ Update failed: {str(e)}")
                    self.stats['failed'] += 1
                    self.update_log.append({
                        'type': 'voicemail_log',
                        'id': db_id,
                        'old_url': update['original_drive_url'],
                        'new_url': update['r2_url'],
                        'status': f'failed: {str(e)}'
                    })
    
    def save_update_log(self):
        """Save update log"""
        if self.update_log:
            with open(UPDATE_LOG_FILE, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['type', 'id', 'old_url', 'new_url', 'status']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.update_log)
            print(f"\nUpdate log saved to: {UPDATE_LOG_FILE}")
    
    def print_summary(self):
        """Print update summary"""
        print("\n" + "="*60)
        print("DATABASE UPDATE SUMMARY")
        print("="*60)
        print(f"Total records: {self.stats['total']}")
        print(f"Updated: {self.stats['updated']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Not found: {self.stats['not_found']}")
        
        success_rate = (self.stats['updated'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
        print(f"\nSuccess rate: {success_rate:.1f}%")


async def main():
    """Main entry point"""
    print("Database Update Tool")
    print("="*60)
    
    # Confirm before proceeding
    print("\nThis will update database URLs from Google Drive to Cloudflare R2.")
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Aborted.")
        return
    
    # Initialize updater
    updater = DatabaseUpdater()
    
    # Update records
    await updater.update_records()
    
    # Save update log
    updater.save_update_log()
    
    # Print summary
    updater.print_summary()
    
    print("\n" + "="*60)
    print("Migration complete!")
    print("\nNext steps:")
    print("1. Test a few URLs to ensure they work")
    print("2. Update your application code to use R2 for new uploads")
    print("3. Keep the downloaded files as backup if needed")


if __name__ == "__main__":
    asyncio.run(main())