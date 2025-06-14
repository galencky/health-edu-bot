"""Storage configuration for different deployment environments"""
import os
from enum import Enum

class StorageBackend(Enum):
    LOCAL = "local"
    GOOGLE_DRIVE = "google_drive"
    MEMORY = "memory"  # For ephemeral deployments

def get_storage_backend() -> StorageBackend:
    """Determine storage backend based on environment"""
    # Force memory storage if explicitly set
    if os.getenv("USE_MEMORY_STORAGE", "").lower() == "true":
        return StorageBackend.MEMORY
    
    # Check if we're on cloud platform (ephemeral filesystem)
    # Render, Heroku, Railway, etc. typically don't have persistent local storage
    is_cloud = (
        os.getenv("RENDER", "").lower() == "true" or
        os.getenv("RENDER_EXTERNAL_URL") or  # Render sets this
        os.getenv("DYNO") or  # Heroku
        os.getenv("RAILWAY_ENVIRONMENT") or  # Railway
        os.getenv("PORT") and not os.path.exists("/home")  # Generic cloud indicator
    )
    
    if is_cloud:
        # Use Google Drive if configured, otherwise memory
        if os.getenv("GOOGLE_DRIVE_FOLDER_ID") and os.getenv("GOOGLE_CREDS_B64"):
            return StorageBackend.GOOGLE_DRIVE
        return StorageBackend.MEMORY
    
    # Local development or persistent filesystem
    return StorageBackend.LOCAL

# Get current backend
STORAGE_BACKEND = get_storage_backend()

# Configure TTS storage
TTS_USE_MEMORY = STORAGE_BACKEND == StorageBackend.MEMORY
TTS_USE_DRIVE = STORAGE_BACKEND == StorageBackend.GOOGLE_DRIVE

# Debug info
print(f"📁 Storage backend: {STORAGE_BACKEND.value}")
print(f"🧠 Memory storage: {TTS_USE_MEMORY}")
print(f"☁️ Drive storage: {TTS_USE_DRIVE}")
print(f"🌐 PORT env: {os.getenv('PORT', 'not set')}")
print(f"🏠 /home exists: {os.path.exists('/home')}")
print(f"📡 RENDER_EXTERNAL_URL: {os.getenv('RENDER_EXTERNAL_URL', 'not set')}")