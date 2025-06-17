"""
Retry utilities for handling network instability and transient failures.
"""
import time
import random
from functools import wraps
from typing import Callable, Any, Optional, Tuple, Type
import traceback

class RetryError(Exception):
    """Raised when all retry attempts are exhausted"""
    def __init__(self, message: str, last_error: Optional[Exception] = None):
        super().__init__(message)
        self.last_error = last_error

def exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None
) -> Callable:
    """
    Decorator that implements exponential backoff retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Add randomization to prevent thundering herd
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback function called on each retry with (attempt_number, exception)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        # Last attempt failed
                        raise RetryError(
                            f"Failed after {max_retries + 1} attempts: {str(e)}",
                            last_error=e
                        )
                    
                    # Calculate delay with exponential backoff
                    delay = min(initial_delay * (exponential_base ** attempt), max_delay)
                    
                    # Add jitter if enabled
                    if jitter:
                        delay = delay * (0.5 + random.random() * 0.5)
                    
                    # Call retry callback if provided
                    if on_retry:
                        try:
                            on_retry(attempt + 1, e)
                        except Exception as callback_error:
                            print(f"Error in retry callback: {callback_error}")
                    
                    # Log retry attempt
                    print(f"[RETRY] Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                    print(f"[RETRY] Retrying in {delay:.2f} seconds...")
                    
                    time.sleep(delay)
            
            # This should never be reached due to the raise in the loop
            raise RetryError(
                f"Unexpected retry exhaustion",
                last_error=last_exception
            )
        
        return wrapper
    return decorator

