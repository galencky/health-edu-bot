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

def retry_with_timeout(
    func: Callable,
    args: tuple = (),
    kwargs: dict = None,
    max_retries: int = 3,
    timeout: float = 30.0,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Any:
    """
    Execute a function with retry logic and timeout.
    
    Args:
        func: Function to execute
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function
        max_retries: Maximum number of retries
        timeout: Timeout in seconds for each attempt
        retry_exceptions: Exceptions that trigger a retry
    
    Returns:
        The function's return value
        
    Raises:
        RetryError: If all retries are exhausted
    """
    import signal
    import threading
    
    if kwargs is None:
        kwargs = {}
    
    def timeout_handler():
        raise TimeoutError(f"Operation timed out after {timeout} seconds")
    
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            # For non-Unix systems or when signal is not available
            result = [None]
            exception = [None]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout)
            
            if thread.is_alive():
                raise TimeoutError(f"Operation timed out after {timeout} seconds")
            
            if exception[0]:
                raise exception[0]
            
            return result[0]
            
        except retry_exceptions as e:
            last_error = e
            
            if attempt == max_retries:
                raise RetryError(
                    f"Failed after {max_retries + 1} attempts: {str(e)}",
                    last_error=e
                )
            
            delay = min(1.0 * (2 ** attempt), 30.0)
            print(f"[RETRY] Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            print(f"[RETRY] Retrying in {delay:.2f} seconds...")
            time.sleep(delay)
    
    raise RetryError("Unexpected retry exhaustion", last_error=last_error)