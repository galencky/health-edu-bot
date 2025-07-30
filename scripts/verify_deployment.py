#!/usr/bin/env python3
"""
Verify deployment readiness - checks that all required files and imports are present
"""
import os
import sys

def check_file_exists(filepath, description):
    """Check if a required file exists"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ MISSING {description}: {filepath}")
        return False

def main():
    print("🔍 Verifying MededBot deployment readiness...\n")
    
    all_good = True
    
    # Check main application files
    print("📁 Core Application Files:")
    all_good &= check_file_exists("main.py", "Main application")
    all_good &= check_file_exists("requirements.txt", "Dependencies")
    all_good &= check_file_exists("Dockerfile", "Docker configuration")
    all_good &= check_file_exists("docker-compose.yml", "Docker Compose")
    all_good &= check_file_exists(".env", "Environment configuration")
    
    # Check core directories
    print("\n📁 Core Directories:")
    all_good &= check_file_exists("handlers/", "Handlers directory")
    all_good &= check_file_exists("services/", "Services directory")
    all_good &= check_file_exists("routes/", "Routes directory")
    all_good &= check_file_exists("utils/", "Utils directory")
    all_good &= check_file_exists("models/", "Models directory")
    
    # Check key service files
    print("\n📁 Key Service Files:")
    all_good &= check_file_exists("utils/r2_service.py", "R2 storage service")
    all_good &= check_file_exists("utils/database.py", "Database service")
    all_good &= check_file_exists("utils/logging.py", "Logging service")
    all_good &= check_file_exists("services/gemini_service.py", "Gemini AI service")
    all_good &= check_file_exists("services/tts_service.py", "TTS service")
    all_good &= check_file_exists("handlers/line_handler.py", "LINE handler")
    
    # Check deployment docs
    print("\n📁 Deployment Documentation:")
    all_good &= check_file_exists("README.md", "Project README")
    all_good &= check_file_exists("docs/DEPLOYMENT.md", "Deployment guide")
    all_good &= check_file_exists("docs/RENDER_DEPLOYMENT.md", "Render deployment")
    
    # Check that archive exists but old google drive service is moved
    print("\n📁 Cleanup Verification:")
    if not os.path.exists("utils/google_drive_service.py"):
        print("✅ Old Google Drive service archived")
    else:
        print("❌ Old Google Drive service still in utils/")
        all_good = False
        
    if os.path.exists("archive/"):
        print("✅ Archive directory created")
    else:
        print("⚠️  No archive directory (OK if fresh deployment)")
    
    # Summary
    print("\n" + "="*50)
    if all_good:
        print("✅ All checks passed! Project is ready for deployment.")
        print("\nNext steps:")
        print("1. Ensure .env file has correct R2 credentials")
        print("2. Run: docker-compose build")
        print("3. Run: docker-compose up -d")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())