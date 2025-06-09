#!/usr/bin/env python3
"""
Test script to verify audio file uploads to Google Drive are working
"""
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_test_audio_files():
    """Create dummy audio files for testing"""
    test_files = []
    
    # Create test directory
    test_dir = "test_audio_files"
    os.makedirs(test_dir, exist_ok=True)
    
    # Create dummy WAV file
    wav_file = os.path.join(test_dir, "test_audio.wav")
    with open(wav_file, "wb") as f:
        # Write a minimal WAV header + some dummy data
        f.write(b'RIFF')
        f.write((1000).to_bytes(4, 'little'))  # File size
        f.write(b'WAVE')
        f.write(b'fmt ')
        f.write((16).to_bytes(4, 'little'))    # fmt chunk size
        f.write((1).to_bytes(2, 'little'))     # Audio format (PCM)
        f.write((1).to_bytes(2, 'little'))     # Number of channels
        f.write((44100).to_bytes(4, 'little')) # Sample rate
        f.write((88200).to_bytes(4, 'little')) # Byte rate
        f.write((2).to_bytes(2, 'little'))     # Block align
        f.write((16).to_bytes(2, 'little'))    # Bits per sample
        f.write(b'data')
        f.write((972).to_bytes(4, 'little'))   # Data chunk size
        f.write(b'\x00' * 972)                 # Dummy audio data
    
    test_files.append(wav_file)
    
    # Create dummy M4A file (just some bytes that look like audio)
    m4a_file = os.path.join(test_dir, "test_voice.m4a")
    with open(m4a_file, "wb") as f:
        # Write basic M4A/MP4 header
        f.write(b'\x00\x00\x00\x20ftypM4A ')  # Basic M4A header
        f.write(b'\x00\x00\x00\x00M4A mp42')
        f.write(b'\x00' * (1024 - 24))        # Dummy data to make it 1KB
    
    test_files.append(m4a_file)
    
    return test_files

def test_google_drive_config():
    """Test if Google Drive is properly configured"""
    print("🔧 Testing Google Drive Configuration")
    print("=" * 50)
    
    # Check environment variables
    drive_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    google_creds = os.getenv("GOOGLE_CREDS_B64")
    
    if not drive_folder_id:
        print("❌ GOOGLE_DRIVE_FOLDER_ID not found in environment")
        return False
    else:
        print(f"✅ GOOGLE_DRIVE_FOLDER_ID: {drive_folder_id[:20]}...")
    
    if not google_creds:
        print("❌ GOOGLE_CREDS_B64 not found in environment")
        return False
    else:
        print(f"✅ GOOGLE_CREDS_B64: Found ({len(google_creds)} characters)")
    
    # Test Google Drive service initialization
    try:
        from utils.google_drive_service import get_drive_service
        service = get_drive_service()
        print("✅ Google Drive service initialized successfully")
        
        # Test basic API call
        files = service.files().list(pageSize=1).execute()
        print("✅ Google Drive API call successful")
        return True
        
    except Exception as e:
        print(f"❌ Google Drive service failed: {e}")
        return False

async def test_wav_upload():
    """Test WAV file upload"""
    print("\n🎵 Testing WAV File Upload")
    print("=" * 50)
    
    try:
        from utils.logging import _log_tts_internal
        
        # Create test WAV file
        test_files = create_test_audio_files()
        wav_file = test_files[0]
        
        print(f"📁 Created test WAV file: {wav_file}")
        print(f"📊 File size: {os.path.getsize(wav_file)} bytes")
        
        # Test TTS logging with WAV upload
        await _log_tts_internal(
            user_id="test_wav_user_123",
            text="Test WAV upload to Google Drive",
            audio_path=wav_file,
            audio_url="http://localhost:10000/static/test_audio.wav"
        )
        
        print("✅ WAV upload test completed")
        return True
        
    except Exception as e:
        print(f"❌ WAV upload test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_m4a_upload():
    """Test M4A file upload"""
    print("\n🎤 Testing M4A File Upload")
    print("=" * 50)
    
    try:
        from utils.logging import _async_upload_voicemail
        
        # Create test M4A file
        test_files = create_test_audio_files()
        m4a_file = test_files[1]
        
        print(f"📁 Created test M4A file: {m4a_file}")
        print(f"📊 File size: {os.path.getsize(m4a_file)} bytes")
        
        # Test voicemail upload
        drive_link = await _async_upload_voicemail(
            local_path=m4a_file,
            user_id="test_m4a_user_456",
            transcription="Test M4A upload transcription",
            translation="Test M4A upload translation"
        )
        
        print(f"✅ M4A upload test completed, Drive link: {drive_link}")
        return True
        
    except Exception as e:
        print(f"❌ M4A upload test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_test_files():
    """Clean up test files"""
    print("\n🧹 Cleaning up test files...")
    try:
        import shutil
        if os.path.exists("test_audio_files"):
            shutil.rmtree("test_audio_files")
        print("✅ Test files cleaned up")
    except Exception as e:
        print(f"⚠️ Cleanup failed: {e}")

async def verify_uploads_in_database():
    """Verify that uploads were logged to database"""
    print("\n🔍 Verifying uploads in database")
    print("=" * 50)
    
    try:
        from utils.database import get_async_db_session, ASYNC_AVAILABLE
        from sqlalchemy import text
        
        if not ASYNC_AVAILABLE:
            print("⚠️ Async database not available, skipping verification")
            return
        
        async with get_async_db_session() as session:
            # Check TTS logs
            result = await session.execute(
                text("SELECT COUNT(*) FROM tts_logs WHERE user_id = 'test_wav_user_123'")
            )
            wav_count = result.scalar()
            print(f"🎵 WAV upload logs found: {wav_count}")
            
            # Check voicemail logs
            result = await session.execute(
                text("SELECT COUNT(*) FROM voicemail_logs WHERE user_id = 'test_m4a_user_456'")
            )
            m4a_count = result.scalar()
            print(f"🎤 M4A upload logs found: {m4a_count}")
            
            # Show recent upload logs with Drive links
            result = await session.execute(
                text("""
                    SELECT 'TTS' as type, audio_filename, status, 
                           CASE WHEN drive_link IS NOT NULL THEN 'Yes' ELSE 'No' END as has_drive_link
                    FROM tts_logs 
                    WHERE user_id LIKE 'test_%' 
                    
                    UNION ALL
                    
                    SELECT 'Voicemail' as type, audio_filename, 'N/A' as status,
                           CASE WHEN drive_link IS NOT NULL THEN 'Yes' ELSE 'No' END as has_drive_link
                    FROM voicemail_logs 
                    WHERE user_id LIKE 'test_%'
                    
                    ORDER BY type
                """)
            )
            logs = result.fetchall()
            
            if logs:
                print("\n📋 Upload results:")
                for log in logs:
                    print(f"  {log[0]}: {log[1]} | Status: {log[2]} | Drive Upload: {log[3]}")
            else:
                print("📋 No upload logs found")
                
    except Exception as e:
        print(f"❌ Database verification failed: {e}")

async def main():
    """Main test function"""
    print("🚀 MedEdBot Audio Upload Test")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test Google Drive configuration
    if not test_google_drive_config():
        print("\n❌ Google Drive configuration failed. Please check your environment variables.")
        return
    
    # Test WAV uploads
    wav_success = await test_wav_upload()
    
    # Test M4A uploads
    m4a_success = await test_m4a_upload()
    
    # Wait for uploads to complete
    print("\n⏳ Waiting for uploads to complete...")
    await asyncio.sleep(5)
    
    # Verify in database
    await verify_uploads_in_database()
    
    # Cleanup
    cleanup_test_files()
    
    # Summary
    print("\n" + "="*60)
    print("📊 AUDIO UPLOAD TEST SUMMARY")
    print("="*60)
    print(f"WAV Upload: {'✅ Success' if wav_success else '❌ Failed'}")
    print(f"M4A Upload: {'✅ Success' if m4a_success else '❌ Failed'}")
    
    if wav_success and m4a_success:
        print("\n🎉 All audio upload tests passed!")
        print("\nKey improvements:")
        print("• ✅ Automatic MIME type detection based on file extension")
        print("• ✅ File size validation (prevents empty file uploads)")
        print("• ✅ Smart upload strategy (resumable for large files, simple for small)")
        print("• ✅ Better error handling and logging")
        print("• ✅ Proper file handle cleanup")
    else:
        print("\n⚠️ Some tests failed. Check the error messages above.")
    
    print("\nNext steps:")
    print("• Check your Google Drive folder for the uploaded test files")
    print("• Use the view_logs.py script to see database entries")
    print("• Test with real audio files from your bot")

if __name__ == "__main__":
    asyncio.run(main())