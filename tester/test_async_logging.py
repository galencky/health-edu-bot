#!/usr/bin/env python3
"""
Test script for async logging functionality
"""
import os
import asyncio
from dotenv import load_dotenv
from urllib.parse import urlparse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Load environment variables
load_dotenv()

async def test_connection():
    """Test basic database connection"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return False
    
    parsed = urlparse(database_url)
    async_url = f"postgresql+asyncpg://{parsed.username}:{parsed.password}@{parsed.hostname}{parsed.path}?ssl=require"
    
    try:
        engine = create_async_engine(async_url, echo=True)
        async with engine.connect() as conn:
            result = await conn.execute(text("select 'hello world'"))
            print("✅ Database connection successful:", result.fetchall())
        await engine.dispose()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

async def test_logging():
    """Test logging functions"""
    from utils.logging import _async_log_chat
    from utils.database import get_async_db_session
    
    try:
        # Test chat logging
        await _async_log_chat(
            user_id="test_user_123",
            message="Test message",
            reply="Test reply",
            session={"test": "data"},
            action_type="test_action",
            gemini_call="no"
        )
        print("✅ Chat logging successful")
        
        # Verify the log was created
        async with get_async_db_session() as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM chat_logs WHERE user_id = 'test_user_123'")
            )
            count = result.scalar()
            print(f"✅ Found {count} test log entries in database")
        
        return True
    except Exception as e:
        print(f"❌ Logging test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("🔄 Testing async database connection...")
    if not await test_connection():
        return
    
    print("\n🔄 Testing async logging functions...")
    if not await test_logging():
        return
    
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(main())