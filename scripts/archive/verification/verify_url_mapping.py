#!/usr/bin/env python3
"""
Verify URL mapping between Google Drive URLs in database and actual files in R2
Creates a mapping table with confidence scores based on filename and timestamp matching
Uses local Google Drive directory for additional verification
"""
import os
import sys
import re
import asyncio
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import boto3
from botocore.config import Config

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from utils.database import get_async_db_session, ChatLog, TTSLog, VoicemailLog
from sqlalchemy import select

@dataclass
class DatabaseRecord:
    """Represents a record from the database"""
    table: str
    id: int
    user_id: str
    timestamp: datetime
    google_drive_url: str
    filename: Optional[str] = None
    google_drive_id: Optional[str] = None
    
@dataclass
class R2File:
    """Represents a file in R2"""
    key: str
    size: int
    last_modified: datetime
    user_id: Optional[str] = None
    timestamp: Optional[datetime] = None

@dataclass
class LocalFile:
    """Represents a file in local Google Drive directory"""
    path: str
    filename: str
    size: int
    modified: datetime
    user_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    
@dataclass
class MappingResult:
    """Mapping result with confidence score"""
    db_record: DatabaseRecord
    r2_file: Optional[R2File]
    local_file: Optional[LocalFile]
    confidence: float
    reason: str
    proposed_r2_url: str

class URLMappingVerifier:
    def __init__(self):
        # Use custom domain for R2 public URL
        self.r2_public_url = 'https://galenchen.uk'
        self.local_drive_path = r"C:\Users\galen\My Drive\2025 archive\社區醫學\MedEdBot - AI 衛教翻譯機器人\ChatbotTexts"
        self.stats = {
            'db_records': 0,
            'r2_files': 0,
            'local_files': 0,
            'perfect_matches': 0,
            'fuzzy_matches': 0,
            'no_matches': 0
        }
        
        # Initialize R2 client
        self.r2_client = boto3.client(
            's3',
            endpoint_url=os.getenv('R2_ENDPOINT_URL'),
            aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
            config=Config(signature_version='s3v4', region_name='auto')
        )
        self.bucket_name = os.getenv('R2_BUCKET_NAME', 'mededbot')
        
    def parse_r2_key(self, key: str) -> Tuple[Optional[str], Optional[datetime]]:
        """Extract user_id and timestamp from R2 key"""
        # Extract filename from key
        filename = os.path.basename(key)
        
        # Pattern 1: U{user_id}-{timestamp}.ext
        pattern1 = r'^(U[a-fA-F0-9]{32})-(\d{8}_\d{6})\.'
        match1 = re.match(pattern1, filename)
        if match1:
            user_id = match1.group(1)
            timestamp_str = match1.group(2)
            timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            return user_id, timestamp
        
        # Pattern 2: U{user_id}_{timestamp}.ext (audio files)
        pattern2 = r'^(U[a-fA-F0-9]{32})_(\d{8}_\d{6})\.'
        match2 = re.match(pattern2, filename)
        if match2:
            user_id = match2.group(1)
            timestamp_str = match2.group(2)
            timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            return user_id, timestamp
        
        # Pattern 3: U{user_id}-{descriptor}-{timestamp}.ext
        pattern3 = r'^(U[a-fA-F0-9]{32})-.*-(\d{8}_\d{6})\.'
        match3 = re.match(pattern3, filename)
        if match3:
            user_id = match3.group(1)
            timestamp_str = match3.group(2)
            timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            return user_id, timestamp
        
        return None, None
    
    def load_local_files(self) -> Dict[str, List[LocalFile]]:
        """Load all files from local Google Drive directory organized by user_id"""
        files_by_user = {}
        
        if not os.path.exists(self.local_drive_path):
            print(f"⚠️  Local Google Drive path not found: {self.local_drive_path}")
            return files_by_user
        
        print(f"📁 Scanning local Google Drive directory...")
        
        for root, dirs, files in os.walk(self.local_drive_path):
            for filename in files:
                if filename.startswith('.') or filename.startswith('~$'):
                    continue
                
                file_path = os.path.join(root, filename)
                try:
                    file_stats = os.stat(file_path)
                    local_file = LocalFile(
                        path=file_path,
                        filename=filename,
                        size=file_stats.st_size,
                        modified=datetime.fromtimestamp(file_stats.st_mtime)
                    )
                    
                    # Parse user_id and timestamp
                    user_id, timestamp = self.parse_r2_key(filename)
                    if user_id:
                        local_file.user_id = user_id
                        local_file.timestamp = timestamp
                        
                        if user_id not in files_by_user:
                            files_by_user[user_id] = []
                        files_by_user[user_id].append(local_file)
                    
                    self.stats['local_files'] += 1
                    
                except Exception as e:
                    print(f"⚠️  Error reading {filename}: {e}")
        
        print(f"📁 Found {self.stats['local_files']} files in local Google Drive")
        return files_by_user
    
    async def check_table_exists(self, session, table_name: str) -> bool:
        """Check if a table exists in the database"""
        try:
            from sqlalchemy import text
            result = await session.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table_name)"),
                {"table_name": table_name}
            )
            return result.scalar()
        except Exception:
            return False
    
    async def load_database_records(self) -> List[DatabaseRecord]:
        """Load all records with Google Drive URLs from database"""
        records = []
        
        async with get_async_db_session() as session:
            # Check which tables exist
            tables_to_check = {
                'chat_logs': True,
                'tts_logs': True,
                'voicemail_logs': True
            }
            
            for table_name in tables_to_check:
                exists = await self.check_table_exists(session, table_name)
                tables_to_check[table_name] = exists
                if not exists:
                    print(f"⚠️  Table '{table_name}' does not exist in database")
            
            # Load chat logs if table exists
            if tables_to_check['chat_logs']:
                result = await session.execute(
                    select(ChatLog).where(
                        ChatLog.gemini_output_url.like('https://drive.google.com%')
                    )
                )
                for log in result.scalars():
                    # Extract Google Drive file ID from URL
                    drive_id = None
                    if log.gemini_output_url:
                        match = re.search(r'/file/d/([a-zA-Z0-9_-]+)/', log.gemini_output_url)
                        if match:
                            drive_id = match.group(1)
                    
                    records.append(DatabaseRecord(
                        table='chat_logs',
                        id=log.id,
                        user_id=log.user_id,
                        timestamp=log.timestamp,
                        google_drive_url=log.gemini_output_url,
                        google_drive_id=drive_id
                    ))
            
            # Load TTS logs if table exists
            if tables_to_check['tts_logs']:
                result = await session.execute(
                    select(TTSLog).where(
                        TTSLog.drive_link.like('https://drive.google.com%')
                    )
                )
                for log in result.scalars():
                    # Extract Google Drive file ID from URL
                    drive_id = None
                    if log.drive_link:
                        match = re.search(r'/file/d/([a-zA-Z0-9_-]+)/', log.drive_link)
                        if match:
                            drive_id = match.group(1)
                    
                    records.append(DatabaseRecord(
                        table='tts_logs',
                        id=log.id,
                        user_id=log.user_id,
                        timestamp=log.timestamp,
                        google_drive_url=log.drive_link,
                        filename=log.audio_filename,
                        google_drive_id=drive_id
                    ))
            
            # Load voicemail logs if table exists
            if tables_to_check['voicemail_logs']:
                result = await session.execute(
                    select(VoicemailLog).where(
                        VoicemailLog.drive_link.like('https://drive.google.com%')
                    )
                )
                for log in result.scalars():
                    # Extract Google Drive file ID from URL
                    drive_id = None
                    if log.drive_link:
                        match = re.search(r'/file/d/([a-zA-Z0-9_-]+)/', log.drive_link)
                        if match:
                            drive_id = match.group(1)
                    
                    records.append(DatabaseRecord(
                        table='voicemail_logs',
                        id=log.id,
                        user_id=log.user_id,
                        timestamp=log.timestamp,
                        google_drive_url=log.drive_link,
                        filename=log.audio_filename,
                        google_drive_id=drive_id
                    ))
        
        self.stats['db_records'] = len(records)
        print(f"📊 Loaded {len(records)} database records with Google Drive URLs")
        return records
    
    def load_r2_files(self) -> Dict[str, List[R2File]]:
        """Load all files from R2 bucket organized by user_id"""
        files_by_user = {}
        
        try:
            paginator = self.r2_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name)
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        r2_file = R2File(
                            key=obj['Key'],
                            size=obj['Size'],
                            last_modified=obj['LastModified']
                        )
                        
                        # Parse user_id and timestamp
                        user_id, timestamp = self.parse_r2_key(obj['Key'])
                        if user_id:
                            r2_file.user_id = user_id
                            r2_file.timestamp = timestamp
                            
                            if user_id not in files_by_user:
                                files_by_user[user_id] = []
                            files_by_user[user_id].append(r2_file)
                        
                        self.stats['r2_files'] += 1
            
            print(f"☁️  Loaded {self.stats['r2_files']} files from R2")
            return files_by_user
            
        except Exception as e:
            print(f"❌ Error loading R2 files: {e}")
            return {}
    
    def calculate_time_difference(self, time1: datetime, time2: datetime) -> float:
        """Calculate time difference in seconds"""
        return abs((time1 - time2).total_seconds())
    
    def find_best_match(self, db_record: DatabaseRecord, r2_files: List[R2File], local_files: List[LocalFile]) -> Tuple[Optional[R2File], Optional[LocalFile], float, str]:
        """Find best matching R2 file for a database record"""
        best_r2_match = None
        best_local_match = None
        best_score = 0.0
        best_reason = ""
        
        # First, try to find local file match
        if local_files:
            for local_file in local_files:
                # For TTS and voicemail, we have exact filenames
                if db_record.filename and db_record.table in ['tts_logs', 'voicemail_logs']:
                    if db_record.filename == local_file.filename:
                        best_local_match = local_file
                        best_score = 1.0
                        best_reason = "Exact local filename match"
                        break
                
                # Match by timestamp
                if local_file.timestamp:
                    time_diff = self.calculate_time_difference(db_record.timestamp, local_file.timestamp)
                    
                    if time_diff <= 60:  # Within 1 minute for local files
                        best_local_match = local_file
                        best_score = 0.95
                        best_reason = f"Local file timestamp match (diff: {time_diff:.1f}s)"
                        break
        
        # Now try to find corresponding R2 file
        if r2_files:
            # If we found a local file, try to match it to R2
            if best_local_match:
                for r2_file in r2_files:
                    # Match by filename
                    if best_local_match.filename in r2_file.key:
                        best_r2_match = r2_file
                        if best_score < 1.0:
                            best_score = 1.0
                            best_reason = "Local file matched to R2 file"
                        break
            
            # If no local match or no R2 match from local, try direct R2 matching
            if not best_r2_match:
                # For TTS and voicemail, we have exact filenames
                if db_record.filename and db_record.table in ['tts_logs', 'voicemail_logs']:
                    for r2_file in r2_files:
                        if db_record.filename in r2_file.key:
                            best_r2_match = r2_file
                            best_score = max(best_score, 0.9)
                            best_reason = "R2 filename match (no local file)"
                            break
                
                # If still no match, try timestamp matching
                if not best_r2_match:
                    for r2_file in r2_files:
                        if not r2_file.timestamp:
                            continue
                        
                        time_diff = self.calculate_time_difference(db_record.timestamp, r2_file.timestamp)
                        
                        # Perfect match (within 2 seconds)
                        if time_diff <= 2:
                            score = 0.95
                            reason = f"R2 timestamp match (diff: {time_diff:.1f}s)"
                        # Good match (within 30 seconds)
                        elif time_diff <= 30:
                            score = 0.85
                            reason = f"Good R2 timestamp match (diff: {time_diff:.1f}s)"
                        # Acceptable match (within 2 minutes)
                        elif time_diff <= 120:
                            score = 0.7
                            reason = f"Acceptable R2 timestamp match (diff: {time_diff:.1f}s)"
                        # Weak match (within 5 minutes)
                        elif time_diff <= 300:
                            score = 0.5
                            reason = f"Weak R2 timestamp match (diff: {time_diff:.1f}s)"
                        else:
                            continue
                        
                        # Check if this is a better match
                        if score > best_score:
                            best_r2_match = r2_file
                            best_score = score
                            best_reason = reason
        
        # If no matches found
        if not best_r2_match and not best_local_match:
            best_reason = "No matches found in R2 or local files"
        
        return best_r2_match, best_local_match, best_score, best_reason
    
    def generate_r2_url(self, db_record: DatabaseRecord, r2_file: Optional[R2File]) -> str:
        """Generate the R2 URL for a record"""
        if r2_file:
            return f"{self.r2_public_url}/{r2_file.key}"
        
        # Generate expected URL even if no match found
        timestamp_str = db_record.timestamp.strftime('%Y%m%d_%H%M%S')
        
        if db_record.table == 'chat_logs':
            filename = f"{db_record.user_id}-{timestamp_str}.txt"
            return f"{self.r2_public_url}/text/{db_record.user_id}/{filename}"
        elif db_record.table == 'tts_logs':
            filename = db_record.filename or f"{db_record.user_id}_{timestamp_str}.wav"
            return f"{self.r2_public_url}/tts_audio/{db_record.user_id}/{filename}"
        elif db_record.table == 'voicemail_logs':
            filename = db_record.filename or f"{db_record.user_id}_{timestamp_str}.wav"
            return f"{self.r2_public_url}/voicemail/{db_record.user_id}/{filename}"
        
        return "UNKNOWN"
    
    async def verify_mappings(self) -> List[MappingResult]:
        """Verify all mappings between database and R2"""
        print("\n🔍 Starting URL mapping verification...\n")
        
        # Load data
        db_records = await self.load_database_records()
        r2_files_by_user = self.load_r2_files()
        local_files_by_user = self.load_local_files()
        
        # Process mappings
        mappings = []
        
        for i, db_record in enumerate(db_records):
            if i % 100 == 0 and i > 0:
                print(f"  Processed {i}/{len(db_records)} records...")
            
            # Get R2 and local files for this user
            user_r2_files = r2_files_by_user.get(db_record.user_id, [])
            user_local_files = local_files_by_user.get(db_record.user_id, [])
            
            # Find best match
            best_r2_match, best_local_match, confidence, reason = self.find_best_match(
                db_record, user_r2_files, user_local_files
            )
            
            # Generate R2 URL
            proposed_url = self.generate_r2_url(db_record, best_r2_match)
            
            # Create mapping result
            mapping = MappingResult(
                db_record=db_record,
                r2_file=best_r2_match,
                local_file=best_local_match,
                confidence=confidence,
                reason=reason,
                proposed_r2_url=proposed_url
            )
            
            mappings.append(mapping)
            
            # Update stats
            if confidence >= 0.9:
                self.stats['perfect_matches'] += 1
            elif confidence >= 0.5:
                self.stats['fuzzy_matches'] += 1
            else:
                self.stats['no_matches'] += 1
        
        return mappings
    
    def save_mapping_report(self, mappings: List[MappingResult], filename: str):
        """Save mapping results to CSV file"""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Table', 'Record ID', 'User ID', 'DB Timestamp', 
                'Google Drive URL', 'Google Drive ID', 'Local File', 'Local Timestamp',
                'R2 File Key', 'R2 Timestamp',
                'Confidence', 'Match Reason', 'Proposed R2 URL'
            ])
            
            for mapping in mappings:
                writer.writerow([
                    mapping.db_record.table,
                    mapping.db_record.id,
                    mapping.db_record.user_id,
                    mapping.db_record.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    mapping.db_record.google_drive_url,
                    mapping.db_record.google_drive_id or 'N/A',
                    mapping.local_file.filename if mapping.local_file else 'NO_LOCAL_MATCH',
                    mapping.local_file.timestamp.strftime('%Y-%m-%d %H:%M:%S') if mapping.local_file and mapping.local_file.timestamp else 'N/A',
                    mapping.r2_file.key if mapping.r2_file else 'NO_R2_MATCH',
                    mapping.r2_file.timestamp.strftime('%Y-%m-%d %H:%M:%S') if mapping.r2_file and mapping.r2_file.timestamp else 'N/A',
                    f"{mapping.confidence:.2f}",
                    mapping.reason,
                    mapping.proposed_r2_url
                ])
        
        print(f"\n📄 Mapping report saved to: {filename}")
    
    def print_summary(self, mappings: List[MappingResult]):
        """Print summary statistics"""
        print("\n" + "=" * 60)
        print("📈 Mapping Verification Summary:")
        print(f"  Total database records: {self.stats['db_records']}")
        print(f"  Total local files: {self.stats['local_files']}")
        print(f"  Total R2 files: {self.stats['r2_files']}")
        print(f"  Perfect matches (≥90%): {self.stats['perfect_matches']}")
        print(f"  Fuzzy matches (50-89%): {self.stats['fuzzy_matches']}")
        print(f"  No matches (<50%): {self.stats['no_matches']}")
        
        # Show problematic records
        print("\n⚠️  Records needing attention:")
        problem_count = 0
        for mapping in mappings:
            if mapping.confidence < 0.5:
                problem_count += 1
                if problem_count <= 10:  # Show first 10
                    print(f"  - {mapping.db_record.table} ID {mapping.db_record.id}: {mapping.reason}")
        
        if problem_count > 10:
            print(f"  ... and {problem_count - 10} more")
        
        # Show confidence distribution
        print("\n📊 Confidence Distribution:")
        confidence_ranges = {
            '100%': 0,
            '90-99%': 0,
            '70-89%': 0,
            '50-69%': 0,
            '<50%': 0
        }
        
        for mapping in mappings:
            if mapping.confidence == 1.0:
                confidence_ranges['100%'] += 1
            elif mapping.confidence >= 0.9:
                confidence_ranges['90-99%'] += 1
            elif mapping.confidence >= 0.7:
                confidence_ranges['70-89%'] += 1
            elif mapping.confidence >= 0.5:
                confidence_ranges['50-69%'] += 1
            else:
                confidence_ranges['<50%'] += 1
        
        for range_name, count in confidence_ranges.items():
            percentage = (count / len(mappings) * 100) if mappings else 0
            print(f"  {range_name}: {count} records ({percentage:.1f}%)")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify URL mapping between Google Drive and R2")
    parser.add_argument('--output', default='url_mapping_report.csv', help='Output CSV file name')
    args = parser.parse_args()
    
    # Check environment
    if not os.getenv("DATABASE_URL"):
        print("❌ Error: DATABASE_URL not found in environment variables")
        return
    
    if not os.getenv("R2_ENDPOINT_URL"):
        print("❌ Error: R2 credentials not found in environment variables")
        return
    
    try:
        verifier = URLMappingVerifier()
        mappings = await verifier.verify_mappings()
        
        # Save report
        verifier.save_mapping_report(mappings, args.output)
        
        # Print summary
        verifier.print_summary(mappings)
        
        print(f"\n✅ Verification complete! Check {args.output} for detailed mapping.")
        
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())