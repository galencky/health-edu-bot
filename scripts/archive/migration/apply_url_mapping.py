#!/usr/bin/env python3
"""
Apply URL mapping from verification results
Only updates high-confidence matches to ensure data integrity
"""
import os
import sys
import csv
import asyncio
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from utils.database import get_async_db_session, ChatLog, TTSLog, VoicemailLog
from sqlalchemy import select, update

class URLMappingApplier:
    def __init__(self, mapping_file: str, confidence_threshold: float = 0.9):
        self.mapping_file = mapping_file
        self.confidence_threshold = confidence_threshold
        self.stats = {
            'total_mappings': 0,
            'high_confidence': 0,
            'chat_logs_updated': 0,
            'tts_logs_updated': 0,
            'voicemail_logs_updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
    def load_mappings(self) -> List[Dict]:
        """Load mapping results from CSV file"""
        mappings = []
        
        with open(self.mapping_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert confidence to float
                row['Confidence'] = float(row['Confidence'])
                mappings.append(row)
        
        self.stats['total_mappings'] = len(mappings)
        print(f"📄 Loaded {len(mappings)} mappings from {self.mapping_file}")
        
        # Count high confidence mappings
        high_conf = [m for m in mappings if m['Confidence'] >= self.confidence_threshold]
        self.stats['high_confidence'] = len(high_conf)
        print(f"✅ Found {len(high_conf)} high-confidence mappings (≥{self.confidence_threshold*100}%)")
        
        return mappings
    
    async def update_database(self, mappings: List[Dict], dry_run: bool = True):
        """Update database with high-confidence mappings"""
        print(f"\n🔄 {'[DRY RUN] ' if dry_run else ''}Updating database...")
        
        # Group mappings by table
        updates_by_table = {
            'chat_logs': [],
            'tts_logs': [],
            'voicemail_logs': []
        }
        
        for mapping in mappings:
            if mapping['Confidence'] >= self.confidence_threshold:
                updates_by_table[mapping['Table']].append(mapping)
        
        async with get_async_db_session() as session:
            # Update chat_logs
            for mapping in updates_by_table['chat_logs']:
                try:
                    if dry_run:
                        print(f"  [DRY RUN] Would update chat_logs ID {mapping['Record ID']}:")
                        print(f"    New URL: {mapping['Proposed R2 URL']}")
                    else:
                        await session.execute(
                            update(ChatLog)
                            .where(ChatLog.id == int(mapping['Record ID']))
                            .values(gemini_output_url=mapping['Proposed R2 URL'])
                        )
                        self.stats['chat_logs_updated'] += 1
                except Exception as e:
                    print(f"  ❌ Error updating chat_logs ID {mapping['Record ID']}: {e}")
                    self.stats['errors'] += 1
            
            # Update tts_logs
            for mapping in updates_by_table['tts_logs']:
                try:
                    if dry_run:
                        print(f"  [DRY RUN] Would update tts_logs ID {mapping['Record ID']}:")
                        print(f"    New URL: {mapping['Proposed R2 URL']}")
                    else:
                        await session.execute(
                            update(TTSLog)
                            .where(TTSLog.id == int(mapping['Record ID']))
                            .values(drive_link=mapping['Proposed R2 URL'])
                        )
                        self.stats['tts_logs_updated'] += 1
                except Exception as e:
                    print(f"  ❌ Error updating tts_logs ID {mapping['Record ID']}: {e}")
                    self.stats['errors'] += 1
            
            # Update voicemail_logs
            for mapping in updates_by_table['voicemail_logs']:
                try:
                    if dry_run:
                        print(f"  [DRY RUN] Would update voicemail_logs ID {mapping['Record ID']}:")
                        print(f"    New URL: {mapping['Proposed R2 URL']}")
                    else:
                        await session.execute(
                            update(VoicemailLog)
                            .where(VoicemailLog.id == int(mapping['Record ID']))
                            .values(drive_link=mapping['Proposed R2 URL'])
                        )
                        self.stats['voicemail_logs_updated'] += 1
                except Exception as e:
                    print(f"  ❌ Error updating voicemail_logs ID {mapping['Record ID']}: {e}")
                    self.stats['errors'] += 1
            
            if not dry_run:
                await session.commit()
                print("  ✅ Changes committed to database")
        
        # Calculate skipped
        self.stats['skipped'] = self.stats['total_mappings'] - self.stats['high_confidence']
    
    async def create_sql_backup(self, mappings: List[Dict]):
        """Create SQL backup for high-confidence updates"""
        backup_file = f"url_mapping_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        
        with open(backup_file, 'w') as f:
            f.write(f"-- URL Mapping Backup\n")
            f.write(f"-- Generated: {datetime.now()}\n")
            f.write(f"-- Confidence threshold: {self.confidence_threshold}\n\n")
            
            for mapping in mappings:
                if mapping['Confidence'] >= self.confidence_threshold:
                    table = mapping['Table']
                    record_id = mapping['Record ID']
                    old_url = mapping['Google Drive URL']
                    
                    if table == 'chat_logs':
                        f.write(f"-- Restore chat_logs ID {record_id}\n")
                        f.write(f"UPDATE chat_logs SET gemini_output_url = '{old_url}' WHERE id = {record_id};\n\n")
                    elif table == 'tts_logs':
                        f.write(f"-- Restore tts_logs ID {record_id}\n")
                        f.write(f"UPDATE tts_logs SET drive_link = '{old_url}' WHERE id = {record_id};\n\n")
                    elif table == 'voicemail_logs':
                        f.write(f"-- Restore voicemail_logs ID {record_id}\n")
                        f.write(f"UPDATE voicemail_logs SET drive_link = '{old_url}' WHERE id = {record_id};\n\n")
        
        print(f"💾 Backup SQL saved to: {backup_file}")
        return backup_file
    
    def print_summary(self):
        """Print summary statistics"""
        print("\n" + "=" * 60)
        print("📈 URL Mapping Application Summary:")
        print(f"  Total mappings: {self.stats['total_mappings']}")
        print(f"  High confidence (≥{self.confidence_threshold*100}%): {self.stats['high_confidence']}")
        print(f"  Chat logs updated: {self.stats['chat_logs_updated']}")
        print(f"  TTS logs updated: {self.stats['tts_logs_updated']}")
        print(f"  Voicemail logs updated: {self.stats['voicemail_logs_updated']}")
        print(f"  Skipped (low confidence): {self.stats['skipped']}")
        print(f"  Errors: {self.stats['errors']}")
        
        total_updated = (self.stats['chat_logs_updated'] + 
                        self.stats['tts_logs_updated'] + 
                        self.stats['voicemail_logs_updated'])
        
        if total_updated > 0:
            print(f"\n✅ Successfully updated {total_updated} records!")
    
    def generate_low_confidence_report(self, mappings: List[Dict]):
        """Generate report of low-confidence mappings for manual review"""
        low_conf_file = f"low_confidence_mappings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        low_conf_mappings = [m for m in mappings if m['Confidence'] < self.confidence_threshold]
        
        if low_conf_mappings:
            with open(low_conf_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=low_conf_mappings[0].keys())
                writer.writeheader()
                writer.writerows(low_conf_mappings)
            
            print(f"\n📋 Low-confidence mappings saved to: {low_conf_file}")
            print(f"   Review these {len(low_conf_mappings)} records manually")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Apply URL mapping from verification results")
    parser.add_argument('mapping_file', nargs='?', default='url_mapping_report.csv',
                       help='Mapping CSV file from verify_url_mapping.py')
    parser.add_argument('--confidence', type=float, default=0.9,
                       help='Minimum confidence threshold (default: 0.9)')
    parser.add_argument('--live', action='store_true',
                       help='Actually update the database (default is dry run)')
    args = parser.parse_args()
    
    # Check if mapping file exists
    if not os.path.exists(args.mapping_file):
        print(f"❌ Error: Mapping file '{args.mapping_file}' not found")
        print("Run verify_url_mapping.py first to generate the mapping file")
        return
    
    # Check environment
    if not os.getenv("DATABASE_URL"):
        print("❌ Error: DATABASE_URL not found in environment variables")
        return
    
    try:
        applier = URLMappingApplier(args.mapping_file, args.confidence)
        
        # Load mappings
        mappings = applier.load_mappings()
        
        if not args.live:
            print("\n⚠️  DRY RUN MODE - No changes will be made")
            print("To apply changes, run with --live flag")
        
        # Create backup if live mode
        if args.live and applier.stats['high_confidence'] > 0:
            await applier.create_sql_backup(mappings)
        
        # Update database
        await applier.update_database(mappings, dry_run=not args.live)
        
        # Generate low confidence report
        applier.generate_low_confidence_report(mappings)
        
        # Print summary
        applier.print_summary()
        
        if not args.live and applier.stats['high_confidence'] > 0:
            print(f"\n💡 To apply these {applier.stats['high_confidence']} updates, run:")
            print(f"   python {sys.argv[0]} {args.mapping_file} --live")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())