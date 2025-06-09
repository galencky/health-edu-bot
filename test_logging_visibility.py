#!/usr/bin/env python3
"""
Test script to demonstrate logging visibility to Neon database
"""
import os
import time
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_sync_logging():
    """Test synchronous logging functions"""
    print("\n" + "="*60)
    print("🧪 TESTING SYNCHRONOUS LOGGING")
    print("="*60)
    
    from utils.logging import log_chat_sync, log_tts_async
    
    # Test chat logging
    print("\n1️⃣ Testing chat logging...")
    log_chat_sync(
        user_id="test_user_sync_123",
        message="Test sync message from test script",
        reply="Test sync reply from logging system",
        session={"test": "sync_session_data"},
        action_type="test_sync_chat",
        gemini_call="no"
    )
    
    # Wait a moment for async thread to complete
    time.sleep(2)
    
    # Test TTS logging
    print("\n2️⃣ Testing TTS logging...")
    # Create a dummy audio file for testing
    test_audio_path = "/tmp/test_audio_sync.wav"
    with open(test_audio_path, "w") as f:
        f.write("dummy audio content")
    
    log_tts_async(
        user_id="test_user_sync_123",
        text="Test TTS text for sync logging",
        audio_path=test_audio_path,
        audio_url="http://localhost:10000/static/test_audio_sync.wav"
    )
    
    # Wait for TTS logging to complete
    print("⏳ Waiting for TTS logging to complete...")
    time.sleep(5)
    
    # Clean up
    if os.path.exists(test_audio_path):
        os.remove(test_audio_path)

async def test_async_logging():
    """Test asynchronous logging functions"""
    print("\n" + "="*60)
    print("🧪 TESTING ASYNCHRONOUS LOGGING")
    print("="*60)
    
    from utils.logging import _async_log_chat, _log_tts_internal, _async_upload_voicemail
    
    # Test async chat logging
    print("\n1️⃣ Testing async chat logging...")
    success = await _async_log_chat(
        user_id="test_user_async_456",
        message="Test async message from test script",
        reply="Test async reply from logging system",
        session={"test": "async_session_data"},
        action_type="test_async_chat",
        gemini_call="no"
    )
    print(f"Chat logging result: {'✅ Success' if success else '❌ Failed'}")
    
    # Test async TTS logging
    print("\n2️⃣ Testing async TTS logging...")
    test_audio_path = "/tmp/test_audio_async.wav"
    with open(test_audio_path, "w") as f:
        f.write("dummy async audio content")
    
    await _log_tts_internal(
        user_id="test_user_async_456",
        text="Test async TTS text for database logging",
        audio_path=test_audio_path,
        audio_url="http://localhost:10000/static/test_audio_async.wav"
    )
    
    # Clean up
    if os.path.exists(test_audio_path):
        os.remove(test_audio_path)

def test_database_connection():
    """Test basic database connectivity"""
    print("\n" + "="*60)
    print("🔌 TESTING DATABASE CONNECTION")
    print("="*60)
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        database_url = os.getenv("CONNECTION_STRING")
    
    if database_url:
        print(f"✅ Database URL found: {database_url[:50]}...")
        
        # Test if we can import database modules
        try:
            from utils.database import ASYNC_AVAILABLE, get_async_db_engine
            print(f"✅ Database module imported successfully")
            print(f"📊 Async support available: {'✅ Yes' if ASYNC_AVAILABLE else '❌ No (using sync fallback)'}")
            
            if ASYNC_AVAILABLE:
                try:
                    engine = get_async_db_engine()
                    print(f"✅ Async database engine created successfully")
                except Exception as e:
                    print(f"❌ Failed to create async database engine: {e}")
            else:
                print("⚠️  Using sync database fallback")
                
        except Exception as e:
            print(f"❌ Failed to import database module: {e}")
    else:
        print("❌ No DATABASE_URL or CONNECTION_STRING found in environment")

async def verify_logs_in_database():
    """Verify that test logs were actually saved to database"""
    print("\n" + "="*60)
    print("🔍 VERIFYING LOGS IN DATABASE")
    print("="*60)
    
    try:
        from utils.database import ASYNC_AVAILABLE, get_async_db_session
        from sqlalchemy import text
        
        if not ASYNC_AVAILABLE:
            print("⚠️  Async not available, skipping database verification")
            return
        
        async with get_async_db_session() as session:
            # Check for test chat logs
            result = await session.execute(
                text("SELECT COUNT(*) FROM chat_logs WHERE user_id LIKE 'test_user_%'")
            )
            chat_count = result.scalar()
            print(f"📝 Test chat logs found: {chat_count}")
            
            # Check for test TTS logs
            result = await session.execute(
                text("SELECT COUNT(*) FROM tts_logs WHERE user_id LIKE 'test_user_%'")
            )
            tts_count = result.scalar()
            print(f"🔊 Test TTS logs found: {tts_count}")
            
            # Show recent test logs
            result = await session.execute(
                text("""
                    SELECT timestamp, user_id, action_type, LEFT(message, 30) as message_preview
                    FROM chat_logs 
                    WHERE user_id LIKE 'test_user_%' 
                    ORDER BY timestamp DESC 
                    LIMIT 5
                """)
            )
            recent_logs = result.fetchall()
            
            if recent_logs:
                print("\n📋 Recent test logs:")
                for log in recent_logs:
                    timestamp = log[0].strftime("%H:%M:%S")
                    print(f"  {timestamp} | {log[1]} | {log[2]} | {log[3]}...")
            else:
                print("📋 No recent test logs found")
                
    except Exception as e:
        print(f"❌ Failed to verify logs in database: {e}")

async def main():
    """Main test function"""
    print("🚀 MedEdBot Database Logging Visibility Test")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test database connection first
    test_database_connection()
    
    # Test synchronous logging
    test_sync_logging()
    
    # Test asynchronous logging
    await test_async_logging()
    
    # Wait a moment for all async operations to complete
    print("\n⏳ Waiting for all logging operations to complete...")
    await asyncio.sleep(3)
    
    # Verify logs were saved
    await verify_logs_in_database()
    
    print("\n" + "="*60)
    print("✅ LOGGING VISIBILITY TEST COMPLETED")
    print("="*60)
    print("\nWhat to look for in the output:")
    print("• ✅ [DB] or [DB-SYNC] messages = successful database saves")
    print("• ❌ [DB] or [DB-SYNC] messages = failed database saves")
    print("• 🔄 [LOGGING] messages = logging operations starting")
    print("• ☁️ uploaded / 💾 local only = Google Drive status")
    print("\nCheck your Neon database for the test logs!")

if __name__ == "__main__":
    asyncio.run(main())