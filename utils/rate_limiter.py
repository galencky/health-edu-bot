"""Rate limiting utilities for API protection"""
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Optional, Callable
from functools import wraps

class RateLimiter:
    """Token bucket rate limiter with sliding window"""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(deque)
        self.lock = Lock()
    
    def is_allowed(self, key: str) -> bool:
        """
        Check if request is allowed for the given key
        
        Args:
            key: Unique identifier (e.g., user_id, IP address)
            
        Returns:
            bool: True if request is allowed, False if rate limit exceeded
        """
        with self.lock:
            now = time.time()
            
            # Get request timestamps for this key
            timestamps = self.requests[key]
            
            # Remove old timestamps outside the window
            while timestamps and timestamps[0] < now - self.window_seconds:
                timestamps.popleft()
            
            # Check if limit exceeded
            if len(timestamps) >= self.max_requests:
                return False
            
            # Add current timestamp
            timestamps.append(now)
            
            # Automatic cleanup: Remove old keys periodically (every 100 requests)
            if len(self.requests) > 0 and sum(len(ts) for ts in self.requests.values()) % 100 == 0:
                self._cleanup_old_entries_internal(now)
            
            return True
    
    def reset(self, key: str) -> None:
        """Reset rate limit for a specific key"""
        with self.lock:
            if key in self.requests:
                del self.requests[key]
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests for a key"""
        with self.lock:
            now = time.time()
            timestamps = self.requests[key]
            
            # Remove old timestamps
            while timestamps and timestamps[0] < now - self.window_seconds:
                timestamps.popleft()
            
            return max(0, self.max_requests - len(timestamps))
    
    def _cleanup_old_entries_internal(self, now: float, max_age_seconds: int = 3600) -> None:
        """Internal cleanup method - must be called with lock held"""
        keys_to_remove = []
        
        for key, timestamps in self.requests.items():
            # Remove old timestamps from this key
            while timestamps and timestamps[0] < now - self.window_seconds:
                timestamps.popleft()
            
            # If no timestamps remain or all are very old, mark for removal
            if not timestamps or (timestamps and timestamps[-1] < now - max_age_seconds):
                keys_to_remove.append(key)
        
        # Remove empty/old keys
        for key in keys_to_remove:
            del self.requests[key]
    
    def cleanup_old_entries(self, max_age_seconds: int = 7200) -> int:
        """
        Clean up old entries to prevent memory leaks
        
        NOTE: This should be called periodically (e.g., hourly) to prevent unbounded memory growth
        
        Args:
            max_age_seconds: Remove keys with no recent activity (default: 2 hours)
            
        Returns:
            int: Number of keys removed
        """
        removed_count = 0
        with self.lock:
            now = time.time()
            keys_to_remove = []
            
            for key, timestamps in self.requests.items():
                # Remove old timestamps from this key
                while timestamps and timestamps[0] < now - self.window_seconds:
                    timestamps.popleft()
                
                # If no timestamps remain or all are very old, mark for removal
                if not timestamps or (timestamps and timestamps[-1] < now - max_age_seconds):
                    keys_to_remove.append(key)
            
            # Remove empty/old keys
            for key in keys_to_remove:
                del self.requests[key]
                removed_count += 1
        
        return removed_count

# Global rate limiters for different services
gemini_limiter = RateLimiter(max_requests=30, window_seconds=60)  # 30 requests per minute
tts_limiter = RateLimiter(max_requests=20, window_seconds=60)     # 20 TTS per minute

def rate_limit(limiter: RateLimiter, key_func: Optional[Callable] = None):
    """
    Decorator for rate limiting functions
    
    Args:
        limiter: RateLimiter instance to use
        key_func: Function to extract rate limit key from arguments
    """
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Extract key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Default: use first argument as key
                key = str(args[0]) if args else "default"
            
            # Check rate limit
            if not limiter.is_allowed(key):
                remaining = limiter.get_remaining(key)
                raise RateLimitExceeded(
                    f"Rate limit exceeded. Try again in {limiter.window_seconds} seconds. "
                    f"Remaining requests: {remaining}"
                )
            
            return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Default: use first argument as key
                key = str(args[0]) if args else "default"
            
            # Check rate limit
            if not limiter.is_allowed(key):
                remaining = limiter.get_remaining(key)
                raise RateLimitExceeded(
                    f"Rate limit exceeded. Try again in {limiter.window_seconds} seconds. "
                    f"Remaining requests: {remaining}"
                )
            
            return await func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""
    pass

# Example usage:
# @rate_limit(gemini_limiter)
# def call_gemini_api(user_id: str, prompt: str):
#     # API call implementation
#     pass