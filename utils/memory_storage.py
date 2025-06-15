"""In-memory storage for ephemeral deployments (e.g., Render)"""
import io
import time
from typing import Dict, Optional, Tuple
from threading import Lock
from collections import OrderedDict

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
        with self.lock:
            # Remove if exists
            if filename in self.files:
                self.remove(filename)
            
            # Check size limit
            if len(data) > self.max_size_bytes:
                print(f"⚠️ File {filename} too large ({len(data)} bytes)")
                return False
            
            # Evict old files if necessary
            # Check if we exceed cleanup threshold or will exceed max size
            while ((self.total_size + len(data) > self.cleanup_threshold_bytes) or 
                   (self.total_size + len(data) > self.max_size_bytes)):
                if not self.files:
                    break
                oldest_key = next(iter(self.files))
                self.remove(oldest_key)
                
            # Also check file limit if it's set
            if self.max_files is not None:
                while len(self.files) >= self.max_files:
                    if not self.files:
                        break
                    oldest_key = next(iter(self.files))
                    self.remove(oldest_key)
            
            # Store file
            self.files[filename] = (data, time.time(), content_type)
            self.total_size += len(data)
            
            # Move to end (most recently used)
            self.files.move_to_end(filename)
            
            print(f"💾 Stored {filename} in memory ({len(data)} bytes)")
            return True
    
    def get(self, filename: str) -> Optional[Tuple[bytes, str]]:
        """Get file from memory"""
        with self.lock:
            if filename in self.files:
                data, timestamp, content_type = self.files[filename]
                # Move to end (most recently used)
                self.files.move_to_end(filename)
                return data, content_type
            return None
    
    def remove(self, filename: str) -> bool:
        """Remove file from memory"""
        with self.lock:
            if filename in self.files:
                data, _, _ = self.files[filename]
                self.total_size -= len(data)
                del self.files[filename]
                return True
            return False
    
    def exists(self, filename: str) -> bool:
        """Check if file exists"""
        with self.lock:
            return filename in self.files
    
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

# Global instance with updated configuration
# - Total storage limit: 1GB (1024MB)
# - Cleanup threshold: 250MB (starts removing oldest files when exceeded)
# - No file number limit (removed the 100 files max)
# - 24hr TTL (via cleanup_old_files method)
memory_storage = MemoryStorage()