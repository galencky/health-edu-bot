"""Storage configuration for different deployment environments"""
import os
from enum import Enum

class StorageBackend(Enum):
    LOCAL = "local"
    R2 = "r2"  # Cloudflare R2
    MEMORY = "memory"  # For ephemeral deployments

def get_storage_backend() -> StorageBackend:
    """Determine storage backend based on environment"""
    # Force memory storage if explicitly set
    if os.getenv("USE_MEMORY_STORAGE", "").lower() == "true":
        return StorageBackend.MEMORY
    
    # Check if R2 is configured
    has_r2_config = bool(
        os.getenv("R2_ENDPOINT_URL") and 
        os.getenv("R2_ACCESS_KEY_ID") and
        os.getenv("R2_SECRET_ACCESS_KEY")
    )
    
    # Check if we're on cloud platform (ephemeral filesystem)
    # Render, Heroku, Railway, etc. typically don't have persistent local storage
    is_cloud = (
        os.getenv("RENDER", "").lower() == "true" or
        os.getenv("RENDER_EXTERNAL_URL") or  # Render sets this
        os.getenv("DYNO") or  # Heroku
        os.getenv("RAILWAY_ENVIRONMENT") or  # Railway
        os.getenv("PORT") and not os.path.exists("/home")  # Generic cloud indicator
    )
    
    # TEMP: Force memory storage for debugging
    port = os.getenv("PORT")
    if port and port != "10001":  # Render typically assigns different ports
        print(f"🚨 [STORAGE] Detected cloud deployment (PORT={port}), forcing memory storage")
        return StorageBackend.MEMORY
    
    if is_cloud:
        # Use R2 if configured, otherwise memory
        if has_r2_config:
            return StorageBackend.R2
        return StorageBackend.MEMORY
    
    # Local development or persistent filesystem
    # Use R2 if configured, otherwise local
    if has_r2_config:
        return StorageBackend.R2
    return StorageBackend.LOCAL

# Get current backend
STORAGE_BACKEND = get_storage_backend()

# Configure TTS storage
TTS_USE_MEMORY = STORAGE_BACKEND == StorageBackend.MEMORY
TTS_USE_R2 = STORAGE_BACKEND == StorageBackend.R2

