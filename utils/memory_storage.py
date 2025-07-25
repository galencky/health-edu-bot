"""In-memory storage for ephemeral deployments (e.g., Render)"""
import io
import time
from typing import Dict, Optional, Tuple
from threading import Lock
from collections import OrderedDict
from .validators import sanitize_filename

class MemoryStorage:
    """Thread-safe in-memory storage with LRU eviction"""
    
    def __init__(self, max_files: int = None, max_size_mb: int = 1024):
        self.max_files = max_files  # None means no file number limit
        self.max_size_bytes = max_size_mb * 1024 * 1024  # 1GB total storage limit
        self.cleanup_threshold_bytes = 262144000  # Start cleanup when exceeding 250MB
        self.files: OrderedDict[str, Tuple[bytes, float, str]] = OrderedDict()  # filename -> (data, timestamp, content_type)
        self.total_size = 0
        self.lock = Lock()
    
    def save(self, filename: str, data: bytes, content_type: str = "audio/wav") -> bool:
        """Save file to memory"""
        # Sanitize filename to prevent path traversal
        try:
            safe_filename = sanitize_filename(filename)
        except ValueError as e:
            print(f"⚠️ Invalid filename rejected: {filename} - {e}")
            return False
            
        with self.lock:
            # Remove if exists
            if safe_filename in self.files:
                self.remove(safe_filename)
            
            # Check size limit
            if len(data) > self.max_size_bytes:
                print(f"⚠️ File {safe_filename} too large ({len(data)} bytes)")
                return False
            
            # Simple eviction: remove oldest files until we have space
            while (self.total_size + len(data) > self.max_size_bytes or 
                   (self.max_files and len(self.files) >= self.max_files)):
                if not self.files:
                    break
                oldest_key = next(iter(self.files))
                self.remove(oldest_key)
            
            # Store file
            self.files[safe_filename] = (data, time.time(), content_type)
            self.total_size += len(data)
            
            # Move to end (most recently used)
            self.files.move_to_end(safe_filename)
            
            print(f"💾 Stored {safe_filename} in memory ({len(data)} bytes)")
            return True
    
    def get(self, filename: str) -> Optional[Tuple[bytes, str]]:
        """Get file from memory"""
        # Sanitize filename to prevent path traversal
        try:
            safe_filename = sanitize_filename(filename)
        except ValueError:
            return None
            
        with self.lock:
            if safe_filename in self.files:
                data, timestamp, content_type = self.files[safe_filename]
                # Move to end (most recently used)
                self.files.move_to_end(safe_filename)
                return data, content_type
            return None
    
    def remove(self, filename: str) -> bool:
        """Remove file from memory"""
        # Sanitize filename to prevent path traversal
        try:
            safe_filename = sanitize_filename(filename)
        except ValueError:
            return False
            
        with self.lock:
            if safe_filename in self.files:
                data, _, _ = self.files[safe_filename]
                self.total_size -= len(data)
                del self.files[safe_filename]
                return True
            return False
    
    def exists(self, filename: str) -> bool:
        """Check if file exists"""
        # Sanitize filename to prevent path traversal
        try:
            safe_filename = sanitize_filename(filename)
        except ValueError:
            return False
            
        with self.lock:
            return safe_filename in self.files
    
    def get_info(self) -> Dict[str, any]:
        """Get storage statistics"""
        with self.lock:
            info = {
                "files": len(self.files),
                "total_size_mb": self.total_size / (1024 * 1024),
                "max_size_mb": self.max_size_bytes / (1024 * 1024),
                "cleanup_threshold_mb": self.cleanup_threshold_bytes / (1024 * 1024)
            }
            if self.max_files is not None:
                info["max_files"] = self.max_files
            return info
    
    def cleanup_old_files(self, max_age_seconds: int = 86400):
        """Remove files older than max_age_seconds (default: 24 hours)"""
        with self.lock:
            current_time = time.time()
            files_to_remove = []
            
            for filename, (_, timestamp, _) in self.files.items():
                if current_time - timestamp > max_age_seconds:
                    files_to_remove.append(filename)
            
            for filename in files_to_remove:
                self.remove(filename)
            
            if files_to_remove:
                print(f"🧹 Cleaned up {len(files_to_remove)} old files from memory")
    
    def clear_all(self):
        """Clear all files from memory storage"""
        with self.lock:
            self.files.clear()
            self.total_size = 0
            print("🗑️ Cleared all files from memory storage")

# Global instance with updated configuration
# - Total storage limit: 1GB (1024MB)
# - Cleanup threshold: 250MB (starts removing oldest files when exceeded)
# - No file number limit (removed the 100 files max)
# - 24hr TTL (via cleanup_old_files method)
memory_storage = MemoryStorage()