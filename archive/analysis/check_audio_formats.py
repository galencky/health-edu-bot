#!/usr/bin/env python3
"""
Check audio file formats in database
"""
import os
import sys
import asyncio
from collections import Counter
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from utils.database import get_async_db_session, TTSLog
from sqlalchemy import select

async def check_formats():
    """Check audio file formats"""
    print("🔍 Checking audio file formats in database...\n")
    
    extensions = Counter()
    sample_files = {}
    
    async with get_async_db_session() as session:
        # Check TTS logs
        result = await session.execute(
            select(TTSLog).where(TTSLog.audio_filename.isnot(None))
        )
        
        for log in result.scalars():
            if log.audio_filename:
                # Get extension
                ext = os.path.splitext(log.audio_filename)[1].lower()
                extensions[ext] += 1
                
                # Save sample for each extension
                if ext not in sample_files:
                    sample_files[ext] = {
                        'filename': log.audio_filename,
                        'user_id': log.user_id,
                        'url': log.audio_url or log.drive_link
                    }
    
    print("📊 Audio File Extensions:")
    for ext, count in extensions.most_common():
        print(f"  {ext}: {count} files")
        if ext in sample_files:
            sample = sample_files[ext]
            print(f"    Example: {sample['filename']}")
            print(f"    User: {sample['user_id']}")
            if sample['url']:
                print(f"    URL: {sample['url']}")
        print()

async def main():
    if not os.getenv("DATABASE_URL"):
        print("❌ Error: DATABASE_URL not found")
        return
    
    try:
        await check_formats()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())