#!/usr/bin/env python3
"""
Script to view logs from the MedEdBot database
"""
import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from urllib.parse import urlparse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Load environment variables
load_dotenv()

async def get_db_connection():
    """Get async database connection"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Try legacy CONNECTION_STRING
        database_url = os.getenv("CONNECTION_STRING")
    
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables")
    
    parsed = urlparse(database_url)
    async_url = f"postgresql+asyncpg://{parsed.username}:{parsed.password}@{parsed.hostname}{parsed.path}?ssl=require"
    
    engine = create_async_engine(async_url)
    return engine

async def view_chat_logs(limit=10, user_id=None, hours=24):
    """View recent chat logs"""
    engine = await get_db_connection()
    
    where_clause = "WHERE timestamp >= NOW() - INTERVAL '%s hours'" % hours
    if user_id:
        where_clause += f" AND user_id = '{user_id}'"
    
    query = f"""
    SELECT 
        timestamp,
        user_id,
        LEFT(message, 50) as message_preview,
        LEFT(reply, 50) as reply_preview,
        action_type,
        gemini_call
    FROM chat_logs 
    {where_clause}
    ORDER BY timestamp DESC 
    LIMIT {limit}
    """
    
    async with engine.connect() as conn:
        result = await conn.execute(text(query))
        logs = result.fetchall()
    
    await engine.dispose()
    
    print(f"\n📝 Recent Chat Logs (Last {hours} hours):")
    print("=" * 100)
    for log in logs:
        timestamp = log[0].strftime("%Y-%m-%d %H:%M:%S")
        user_id = log[1][:15] + "..." if len(log[1]) > 15 else log[1]
        message = log[2] + "..." if len(str(log[2])) >= 50 else log[2]
        reply = log[3] + "..." if len(str(log[3])) >= 50 else log[3]
        action = log[4] or "chat"
        gemini = "🤖" if log[5] else "💬"
        
        print(f"{timestamp} | {gemini} {user_id} | {action}")
        print(f"  📤 {message}")
        print(f"  📥 {reply}")
        print("-" * 100)

async def view_tts_logs(limit=10, hours=24):
    """View recent TTS logs"""
    engine = await get_db_connection()
    
    query = f"""
    SELECT 
        timestamp,
        user_id,
        LEFT(text, 50) as text_preview,
        audio_filename,
        status,
        drive_link IS NOT NULL as has_drive_link
    FROM tts_logs 
    WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
    ORDER BY timestamp DESC 
    LIMIT {limit}
    """
    
    async with engine.connect() as conn:
        result = await conn.execute(text(query))
        logs = result.fetchall()
    
    await engine.dispose()
    
    print(f"\n🔊 Recent TTS Logs (Last {hours} hours):")
    print("=" * 100)
    for log in logs:
        timestamp = log[0].strftime("%Y-%m-%d %H:%M:%S")
        user_id = log[1][:15] + "..." if len(log[1]) > 15 else log[1]
        text = log[2] + "..." if len(str(log[2])) >= 50 else log[2]
        filename = log[3] or "N/A"
        status = log[4]
        drive_status = "☁️" if log[5] else "💾"
        
        print(f"{timestamp} | {drive_status} {user_id} | {status}")
        print(f"  📝 {text}")
        print(f"  🎵 {filename}")
        print("-" * 100)

async def view_voicemail_logs(limit=10, hours=24):
    """View recent voicemail logs"""
    engine = await get_db_connection()
    
    query = f"""
    SELECT 
        timestamp,
        user_id,
        audio_filename,
        LEFT(transcription, 50) as transcription_preview,
        LEFT(translation, 50) as translation_preview,
        drive_link IS NOT NULL as has_drive_link
    FROM voicemail_logs 
    WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
    ORDER BY timestamp DESC 
    LIMIT {limit}
    """
    
    async with engine.connect() as conn:
        result = await conn.execute(text(query))
        logs = result.fetchall()
    
    await engine.dispose()
    
    print(f"\n🎤 Recent Voicemail Logs (Last {hours} hours):")
    print("=" * 100)
    for log in logs:
        timestamp = log[0].strftime("%Y-%m-%d %H:%M:%S")
        user_id = log[1][:15] + "..." if len(log[1]) > 15 else log[1]
        filename = log[2]
        transcription = log[3] + "..." if len(str(log[3])) >= 50 else log[3]
        translation = log[4] + "..." if len(str(log[4])) >= 50 else log[4]
        drive_status = "☁️" if log[5] else "💾"
        
        print(f"{timestamp} | {drive_status} {user_id}")
        print(f"  🎵 {filename}")
        print(f"  📝 {transcription}")
        print(f"  🌐 {translation}")
        print("-" * 100)

async def view_stats():
    """View database statistics"""
    engine = await get_db_connection()
    
    async with engine.connect() as conn:
        # Chat logs stats
        result = await conn.execute(text("""
            SELECT 
                COUNT(*) as total_chats,
                COUNT(DISTINCT user_id) as unique_users,
                SUM(CASE WHEN gemini_call THEN 1 ELSE 0 END) as gemini_calls,
                COUNT(*) FILTER (WHERE timestamp >= NOW() - INTERVAL '24 hours') as today_chats
            FROM chat_logs
        """))
        chat_stats = result.fetchone()
        
        # TTS logs stats
        result = await conn.execute(text("""
            SELECT 
                COUNT(*) as total_tts,
                COUNT(*) FILTER (WHERE status = 'success') as successful_tts,
                COUNT(*) FILTER (WHERE timestamp >= NOW() - INTERVAL '24 hours') as today_tts
            FROM tts_logs
        """))
        tts_stats = result.fetchone()
        
        # Voicemail logs stats
        result = await conn.execute(text("""
            SELECT 
                COUNT(*) as total_voicemails,
                COUNT(*) FILTER (WHERE timestamp >= NOW() - INTERVAL '24 hours') as today_voicemails
            FROM voicemail_logs
        """))
        voicemail_stats = result.fetchone()
    
    await engine.dispose()
    
    print("\n📊 Database Statistics:")
    print("=" * 50)
    print(f"💬 Chat Logs:")
    print(f"  Total: {chat_stats[0]}")
    print(f"  Unique Users: {chat_stats[1]}")
    print(f"  Gemini Calls: {chat_stats[2]}")
    print(f"  Today: {chat_stats[3]}")
    
    print(f"\n🔊 TTS Logs:")
    print(f"  Total: {tts_stats[0]}")
    print(f"  Successful: {tts_stats[1]}")
    print(f"  Today: {tts_stats[2]}")
    
    print(f"\n🎤 Voicemail Logs:")
    print(f"  Total: {voicemail_stats[0]}")
    print(f"  Today: {voicemail_stats[1]}")

async def main():
    """Main function with interactive menu"""
    print("🔍 MedEdBot Log Viewer")
    print("=" * 50)
    
    while True:
        print("\nChoose an option:")
        print("1. View recent chat logs")
        print("2. View recent TTS logs")
        print("3. View recent voicemail logs")
        print("4. View database statistics")
        print("5. Custom query")
        print("6. Exit")
        
        choice = input("\nEnter choice (1-6): ").strip()
        
        try:
            if choice == "1":
                hours = input("Hours back (default 24): ").strip() or "24"
                limit = input("Number of logs (default 10): ").strip() or "10"
                user_id = input("Filter by user ID (optional): ").strip() or None
                await view_chat_logs(int(limit), user_id, int(hours))
                
            elif choice == "2":
                hours = input("Hours back (default 24): ").strip() or "24"
                limit = input("Number of logs (default 10): ").strip() or "10"
                await view_tts_logs(int(limit), int(hours))
                
            elif choice == "3":
                hours = input("Hours back (default 24): ").strip() or "24"
                limit = input("Number of logs (default 10): ").strip() or "10"
                await view_voicemail_logs(int(limit), int(hours))
                
            elif choice == "4":
                await view_stats()
                
            elif choice == "5":
                query = input("Enter SQL query: ").strip()
                if query:
                    engine = await get_db_connection()
                    async with engine.connect() as conn:
                        result = await conn.execute(text(query))
                        rows = result.fetchall()
                        for row in rows:
                            print(row)
                    await engine.dispose()
                    
            elif choice == "6":
                print("👋 Goodbye!")
                break
                
            else:
                print("Invalid choice. Please try again.")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())