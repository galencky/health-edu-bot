#!/usr/bin/env python3
"""
Fix incorrect R2 URLs that were updated with wrong domain
Changes from: https://7c14fdde93c85ff60383f8ba066ddcf6.r2.cloudflarestorage.com/mededbot/...
           to: https://galenchen.uk/...
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from utils.database import get_async_db_session, ChatLog, TTSLog
from sqlalchemy import select, update, or_

class URLFixer:
    def __init__(self):
        # Multiple possible wrong prefixes
        self.wrong_prefixes = [
            "https://7c14fdde93c85ff60383f8ba066ddcf6.r2.cloudflarestorage.com/mededbot/",
            "https://7c14fdde93c85ff60383f8ba066ddcf6.r2.cloudflarestorage.com/"
        ]
        self.correct_domain = "https://galenchen.uk/"
        self.stats = {
            'chat_logs_fixed': 0,
            'tts_logs_fixed': 0,
            'total_fixed': 0
        }
    
    async def fix_urls(self, dry_run=True):
        """Fix incorrect URLs in database"""
        print(f"🔧 {'[DRY RUN] ' if dry_run else ''}Fixing incorrect R2 URLs...")
        print(f"   Wrong prefixes: {self.wrong_prefixes}")
        print(f"   Correct domain: {self.correct_domain}")
        print()
        
        async with get_async_db_session() as session:
            # Fix chat_logs
            print("📊 Checking chat_logs...")
            
            # Build OR condition for multiple wrong prefixes
            conditions = [ChatLog.gemini_output_url.like(f"{prefix}%") for prefix in self.wrong_prefixes]
            
            result = await session.execute(
                select(ChatLog).where(or_(*conditions))
            )
            chat_logs = result.scalars().all()
            
            print(f"   Found {len(chat_logs)} incorrect URLs in chat_logs")
            
            for log in chat_logs:
                old_url = log.gemini_output_url
                new_url = old_url
                
                # Replace any of the wrong prefixes
                for prefix in self.wrong_prefixes:
                    if old_url.startswith(prefix):
                        # Extract the path after the prefix
                        path = old_url.replace(prefix, "")
                        # Remove 'mededbot/' if it exists at the start of path
                        if path.startswith("mededbot/"):
                            path = path[9:]  # Remove 'mededbot/'
                        new_url = self.correct_domain + path
                        break
                
                if dry_run:
                    print(f"   [DRY RUN] Would fix record {log.id}:")
                    print(f"      Old: {old_url}")
                    print(f"      New: {new_url}")
                else:
                    log.gemini_output_url = new_url
                    self.stats['chat_logs_fixed'] += 1
            
            # Fix tts_logs
            print("\n🔊 Checking tts_logs...")
            
            # Build OR condition for multiple wrong prefixes
            conditions = [TTSLog.drive_link.like(f"{prefix}%") for prefix in self.wrong_prefixes]
            
            result = await session.execute(
                select(TTSLog).where(or_(*conditions))
            )
            tts_logs = result.scalars().all()
            
            print(f"   Found {len(tts_logs)} incorrect URLs in tts_logs")
            
            for log in tts_logs:
                old_url = log.drive_link
                new_url = old_url
                
                # Replace any of the wrong prefixes
                for prefix in self.wrong_prefixes:
                    if old_url.startswith(prefix):
                        # Extract the path after the prefix
                        path = old_url.replace(prefix, "")
                        # Remove 'mededbot/' if it exists at the start of path
                        if path.startswith("mededbot/"):
                            path = path[9:]  # Remove 'mededbot/'
                        new_url = self.correct_domain + path
                        break
                
                if dry_run:
                    print(f"   [DRY RUN] Would fix record {log.id}:")
                    print(f"      Old: {old_url}")
                    print(f"      New: {new_url}")
                else:
                    log.drive_link = new_url
                    self.stats['tts_logs_fixed'] += 1
            
            if not dry_run:
                await session.commit()
                print("\n✅ Changes committed to database")
        
        self.stats['total_fixed'] = self.stats['chat_logs_fixed'] + self.stats['tts_logs_fixed']
        
        print("\n📈 Summary:")
        print(f"   Chat logs fixed: {self.stats['chat_logs_fixed']}")
        print(f"   TTS logs fixed: {self.stats['tts_logs_fixed']}")
        print(f"   Total fixed: {self.stats['total_fixed']}")
        
        if dry_run and self.stats['total_fixed'] == 0 and (len(chat_logs) + len(tts_logs)) > 0:
            print("\n💡 To apply these fixes, run with --live flag")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix incorrect R2 URLs in database")
    parser.add_argument('--live', action='store_true', help='Actually fix the URLs (default is dry run)')
    args = parser.parse_args()
    
    # Check environment
    if not os.getenv("DATABASE_URL"):
        print("❌ Error: DATABASE_URL not found in environment variables")
        return
    
    try:
        fixer = URLFixer()
        await fixer.fix_urls(dry_run=not args.live)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())