#!/usr/bin/env python3
"""
Check current URLs in database to see Google Drive vs R2 distribution
"""
import os
import sys
import asyncio
from dotenv import load_dotenv
from collections import Counter

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from utils.database import get_async_db_session, ChatLog, TTSLog, VoicemailLog
from sqlalchemy import select, func, text

async def check_table_exists(session, table_name: str) -> bool:
    """Check if a table exists in the database"""
    try:
        result = await session.execute(
            text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table_name)"),
            {"table_name": table_name}
        )
        return result.scalar()
    except Exception:
        return False

async def check_urls():
    """Check URL distribution in database"""
    print("🔍 Checking URL distribution in database...\n")
    
    async with get_async_db_session() as session:
        # Check which tables exist
        tables = ['chat_logs', 'tts_logs', 'voicemail_logs']
        existing_tables = []
        
        for table_name in tables:
            if await check_table_exists(session, table_name):
                existing_tables.append(table_name)
            else:
                print(f"⚠️  Table '{table_name}' does not exist in database")
        
        # Check chat_logs if exists
        if 'chat_logs' in existing_tables:
            print("\n📊 Chat Logs (gemini_output_url):")
            result = await session.execute(
                select(
                    func.count(ChatLog.id).label('count'),
                    func.substr(ChatLog.gemini_output_url, 1, 25).label('url_prefix')
                ).where(ChatLog.gemini_output_url.isnot(None))
                .group_by('url_prefix')
            )
            for row in result:
                print(f"  {row.url_prefix}... : {row.count} records")
            
            # Count nulls
            null_count = await session.execute(
                select(func.count(ChatLog.id)).where(ChatLog.gemini_output_url.is_(None))
            )
            print(f"  NULL values: {null_count.scalar()} records")
        
        # Check tts_logs if exists
        if 'tts_logs' in existing_tables:
            print("\n🔊 TTS Logs (drive_link):")
            result = await session.execute(
                select(
                    func.count(TTSLog.id).label('count'),
                    func.substr(TTSLog.drive_link, 1, 25).label('url_prefix')
                ).where(TTSLog.drive_link.isnot(None))
                .group_by('url_prefix')
            )
            for row in result:
                print(f"  {row.url_prefix}... : {row.count} records")
            
            # Count nulls
            null_count = await session.execute(
                select(func.count(TTSLog.id)).where(TTSLog.drive_link.is_(None))
            )
            print(f"  NULL values: {null_count.scalar()} records")
        
        # Check voicemail_logs if exists
        if 'voicemail_logs' in existing_tables:
            print("\n📞 Voicemail Logs (drive_link):")
            result = await session.execute(
                select(
                    func.count(VoicemailLog.id).label('count'),
                    func.substr(VoicemailLog.drive_link, 1, 25).label('url_prefix')
                ).where(VoicemailLog.drive_link.isnot(None))
                .group_by('url_prefix')
            )
            for row in result:
                print(f"  {row.url_prefix}... : {row.count} records")
            
            # Count nulls
            null_count = await session.execute(
                select(func.count(VoicemailLog.id)).where(VoicemailLog.drive_link.is_(None))
            )
            print(f"  NULL values: {null_count.scalar()} records")
        
        # Show sample records
        print("\n📋 Sample Records:")
        
        # Sample chat log if table exists
        if 'chat_logs' in existing_tables:
            result = await session.execute(
                select(ChatLog).where(
                    ChatLog.gemini_output_url.like('https://drive.google.com%')
                ).limit(1)
            )
            chat_sample = result.scalar()
            if chat_sample:
                print(f"\nChat Log Sample (ID: {chat_sample.id}):")
                print(f"  User: {chat_sample.user_id}")
                print(f"  Timestamp: {chat_sample.timestamp}")
                print(f"  URL: {chat_sample.gemini_output_url}")
        
        # Sample TTS log if table exists
        if 'tts_logs' in existing_tables:
            result = await session.execute(
                select(TTSLog).where(
                    TTSLog.drive_link.like('https://drive.google.com%')
                ).limit(1)
            )
            tts_sample = result.scalar()
            if tts_sample:
                print(f"\nTTS Log Sample (ID: {tts_sample.id}):")
                print(f"  User: {tts_sample.user_id}")
                print(f"  Filename: {tts_sample.audio_filename}")
                print(f"  URL: {tts_sample.drive_link}")
        
        if not existing_tables:
            print("\n❌ No tables found in database!")


async def main():
    """Main entry point"""
    # Check environment
    if not os.getenv("DATABASE_URL"):
        print("❌ Error: DATABASE_URL not found in environment variables")
        print("Please ensure your .env file is configured")
        return
    
    try:
        await check_urls()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())