"""
Cleanup utilities for managing temporary files
"""
import os
import time
from pathlib import Path
from datetime import datetime, timedelta

def cleanup_old_tts_files(directory: Path, max_age_hours: int = 24):
    """
    Remove TTS audio files older than specified hours.
    
    Args:
        directory: Path to TTS audio directory
        max_age_hours: Maximum age in hours before deletion (default: 24)
    
    Returns:
        Number of files deleted
    """
    if not directory.exists():
        return 0
    
    deleted_count = 0
    cutoff_time = time.time() - (max_age_hours * 3600)
    
    try:
        for file_path in directory.glob("*.wav"):
            if file_path.is_file():
                # Check file modification time
                if file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        print(f"[CLEANUP] Deleted old TTS file: {file_path.name}")
                    except Exception as e:
                        print(f"[CLEANUP] Failed to delete {file_path.name}: {e}")
    except Exception as e:
        print(f"[CLEANUP] Error during TTS cleanup: {e}")
    
    if deleted_count > 0:
        print(f"[CLEANUP] Deleted {deleted_count} old TTS files")
    
    return deleted_count

def get_directory_size(directory: Path) -> tuple[int, int]:
    """
    Get total size and file count of a directory.
    
    Returns:
        Tuple of (total_size_bytes, file_count)
    """
    total_size = 0
    file_count = 0
    
    try:
        for file_path in directory.glob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
                file_count += 1
    except Exception as e:
        print(f"[CLEANUP] Error calculating directory size: {e}")
    
    return total_size, file_count

def cleanup_tts_directory_by_size(directory: Path, max_size_mb: int = 500):
    """
    Remove oldest TTS files if directory exceeds size limit.
    
    Args:
        directory: Path to TTS audio directory  
        max_size_mb: Maximum directory size in MB
    
    Returns:
        Number of files deleted
    """
    if not directory.exists():
        return 0
    
    max_size_bytes = max_size_mb * 1024 * 1024
    total_size, file_count = get_directory_size(directory)
    
    if total_size <= max_size_bytes:
        return 0
    
    # Get all files with their stats
    files = []
    try:
        for file_path in directory.glob("*.wav"):
            if file_path.is_file():
                stat = file_path.stat()
                files.append((file_path, stat.st_mtime, stat.st_size))
    except Exception as e:
        print(f"[CLEANUP] Error listing files: {e}")
        return 0
    
    # Sort by modification time (oldest first)
    files.sort(key=lambda x: x[1])
    
    deleted_count = 0
    deleted_size = 0
    
    # Delete oldest files until under limit
    for file_path, mtime, size in files:
        if total_size - deleted_size <= max_size_bytes:
            break
        
        try:
            file_path.unlink()
            deleted_count += 1
            deleted_size += size
            print(f"[CLEANUP] Deleted TTS file for size limit: {file_path.name}")
        except Exception as e:
            print(f"⚠️ [CLEANUP] Failed to delete {file_path.name}: {e}")
    
    if deleted_count > 0:
        print(f"[CLEANUP] Deleted {deleted_count} files ({deleted_size / 1024 / 1024:.1f} MB) to stay under {max_size_mb} MB limit")
    
    return deleted_count