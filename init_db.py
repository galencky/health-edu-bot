#!/usr/bin/env python3
"""
Initialize the database tables for MedEdBot logging.
Run this script once to create all necessary tables in your Neon database.
"""

import os
import asyncio
from dotenv import load_dotenv
from utils.database import init_db

async def main():
    # Load environment variables
    load_dotenv()
    
    # Check if connection string exists
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Try legacy CONNECTION_STRING
        database_url = os.getenv("CONNECTION_STRING")
        if database_url:
            print("⚠️  Warning: Using legacy CONNECTION_STRING. Please update to DATABASE_URL in .env")
            os.environ["DATABASE_URL"] = database_url
        else:
            print("❌ Error: DATABASE_URL not found in .env file")
            print("Please add your Neon database connection string to the .env file:")
            print("DATABASE_URL=postgresql://user:password@host/database?sslmode=require")
            return
    
    try:
        print("🔄 Initializing database tables...")
        await init_db()
        print("✅ Database tables created successfully!")
        print("\nCreated tables:")
        print("  - chat_logs (for general chat logging)")
        print("  - tts_logs (for text-to-speech logging)")
        print("  - voicemail_logs (for voicemail transcription logging)")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        print("\nPlease check:")
        print("  1. Your DATABASE_URL is correct")
        print("  2. You have proper permissions to create tables")
        print("  3. Your Neon database is active")

if __name__ == "__main__":
    asyncio.run(main())