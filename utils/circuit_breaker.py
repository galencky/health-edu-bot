"""Circuit breaker pattern for external API calls to prevent cascade failures"""

import time
import asyncio
from typing import Callable, Any, Optional
from enum import Enum
import threading

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking calls due to failures
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass

class CircuitBreaker:
    """
    Circuit breaker for external API calls.
    Prevents cascade failures by temporarily blocking calls to failing services.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        name: str = "unnamed"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.lock = threading.RLock()
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        return (
            self.last_failure_time is not None and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _record_success(self):
        """Record a successful call"""
        with self.lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED
            print(f"🔄 Circuit breaker '{self.name}' reset to CLOSED")
    
    def _record_failure(self):
        """Record a failed call"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                print(f"⚠️ Circuit breaker '{self.name}' OPENED after {self.failure_count} failures")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
        Raises CircuitBreakerError if circuit is open.
        """
        with self.lock:
            # Check if we should attempt to reset
            if self.state == CircuitState.OPEN and self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                print(f"🔄 Circuit breaker '{self.name}' attempting HALF_OPEN")
            
            # Block calls if circuit is open
            if self.state == CircuitState.OPEN:
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Service calls blocked for {self.recovery_timeout}s after {self.failure_count} failures."
                )
        
        # Attempt the call
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception as e:
            self._record_failure()
            raise e
    
    async def acall(self, func: Callable, *args, **kwargs) -> Any:
        """
        Async version of call method.
        """
        with self.lock:
            # Check if we should attempt to reset
            if self.state == CircuitState.OPEN and self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                print(f"🔄 Circuit breaker '{self.name}' attempting HALF_OPEN")
            
            # Block calls if circuit is open
            if self.state == CircuitState.OPEN:
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Service calls blocked for {self.recovery_timeout}s after {self.failure_count} failures."
                )
        
        # Attempt the call
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception as e:
            self._record_failure()
            raise e
    
    def get_status(self) -> dict:
        """Get current circuit breaker status"""
        with self.lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "failure_threshold": self.failure_threshold,
                "last_failure_time": self.last_failure_time,
                "time_until_retry": (
                    max(0, self.recovery_timeout - (time.time() - (self.last_failure_time or 0)))
                    if self.last_failure_time else 0
                )
            }

# Global circuit breakers for external services
gemini_circuit_breaker = CircuitBreaker(
    failure_threshold=5,  # Allow more failures before opening circuit
    recovery_timeout=60,  # Longer recovery time for stability
    expected_exception=Exception,
    name="gemini_api"
)

drive_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=Exception,
    name="google_drive"
)

line_api_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=30,
    expected_exception=Exception,
    name="line_api"
)