"""Storage configuration for different deployment environments"""
import os
from enum import Enum

class StorageBackend(Enum):
    LOCAL = "local"
    GOOGLE_DRIVE = "google_drive"
    MEMORY = "memory"  # For ephemeral deployments

def get_storage_backend() -> StorageBackend:
    """Determine storage backend based on environment"""
    # Check if we're on Render (ephemeral filesystem)
    if os.getenv("RENDER", "").lower() == "true":
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

print(f"📁 Storage backend: {STORAGE_BACKEND.value}")