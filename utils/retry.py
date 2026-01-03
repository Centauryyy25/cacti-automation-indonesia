"""Retry utilities with exponential backoff.

Provides decorators and utilities for implementing robust retry logic
with configurable exponential backoff, jitter, and exception handling.
"""

from __future__ import annotations

import logging
import random
import time
from functools import wraps
from typing import Callable, Type, TypeVar, Any

from config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryExhausted(Exception):
    """Raised when all retry attempts have been exhausted."""
    
    def __init__(self, message: str, last_exception: Exception | None = None):
        super().__init__(message)
        self.last_exception = last_exception


def exponential_backoff(
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float | None = None,
    exponential_base: float | None = None,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
    jitter: bool = True,
    on_retry: Callable[[int, Exception, float], None] | None = None,
) -> Callable:
    """
    Decorator for exponential backoff retry logic.
    
    Args:
        max_attempts: Maximum number of attempts (default from settings)
        base_delay: Initial delay in seconds (default from settings)
        max_delay: Maximum delay in seconds (default from settings)
        exponential_base: Multiplier for exponential backoff (default from settings)
        exceptions: Tuple of exception types to catch and retry
        jitter: Add random jitter to delay (recommended for distributed systems)
        on_retry: Optional callback(attempt, exception, delay) called before each retry
    
    Example:
        @exponential_backoff(max_attempts=5, exceptions=(ConnectionError, TimeoutError))
        def fetch_data():
            return requests.get(url)
    """
    # Use settings defaults if not provided
    _max_attempts = max_attempts or settings.RETRY_MAX_ATTEMPTS
    _base_delay = base_delay or settings.RETRY_BASE_DELAY
    _max_delay = max_delay or settings.RETRY_MAX_DELAY
    _exp_base = exponential_base or settings.RETRY_EXPONENTIAL_BASE
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None
            
            for attempt in range(1, _max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == _max_attempts:
                        logger.error(
                            "Retry exhausted for %s after %d attempts. Last error: %s",
                            func.__name__, attempt, str(e)
                        )
                        raise RetryExhausted(
                            f"Failed after {_max_attempts} attempts: {str(e)}",
                            last_exception=e
                        ) from e
                    
                    # Calculate delay with exponential backoff
                    delay = min(_base_delay * (_exp_base ** (attempt - 1)), _max_delay)
                    
                    # Add jitter (±25%)
                    if jitter:
                        delay = delay * (0.75 + random.random() * 0.5)
                    
                    logger.warning(
                        "Attempt %d/%d for %s failed: %s. Retrying in %.2f seconds...",
                        attempt, _max_attempts, func.__name__, str(e), delay
                    )
                    
                    # Call optional retry callback
                    if on_retry:
                        try:
                            on_retry(attempt, e, delay)
                        except Exception as cb_err:
                            logger.debug("on_retry callback error: %s", cb_err)
                    
                    time.sleep(delay)
            
            # Should not reach here, but just in case
            raise RetryExhausted(
                f"Failed after {_max_attempts} attempts",
                last_exception=last_exception
            )
        
        return wrapper
    return decorator


def retry_with_backoff(
    func: Callable[..., T],
    args: tuple = (),
    kwargs: dict | None = None,
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float | None = None,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
) -> T:
    """
    Execute a function with exponential backoff retry (non-decorator version).
    
    Args:
        func: Function to execute
        args: Positional arguments for func
        kwargs: Keyword arguments for func
        max_attempts: Maximum number of attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Tuple of exception types to catch
    
    Returns:
        Result of func
    
    Raises:
        RetryExhausted: When all attempts fail
    """
    kwargs = kwargs or {}
    
    @exponential_backoff(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exceptions=exceptions,
    )
    def _wrapper():
        return func(*args, **kwargs)
    
    return _wrapper()


class CircuitBreaker:
    """
    Simple circuit breaker pattern implementation.
    
    Prevents repeated calls to a failing service by "opening" the circuit
    after a threshold of failures, then allowing periodic "probe" attempts.
    
    States:
        - CLOSED: Normal operation, calls pass through
        - OPEN: Circuit is tripped, calls fail immediately
        - HALF_OPEN: Testing if service recovered
    """
    
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exceptions: tuple[Type[Exception], ...] = (Exception,),
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions
        
        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._lock_time: float | None = None
    
    @property
    def state(self) -> str:
        """Get current circuit state, checking for timeout transition."""
        if self._state == self.OPEN and self._lock_time:
            if time.time() - self._lock_time >= self.recovery_timeout:
                self._state = self.HALF_OPEN
        return self._state
    
    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function through the circuit breaker."""
        state = self.state
        
        if state == self.OPEN:
            raise RuntimeError(
                f"Circuit breaker is OPEN. Service unavailable. "
                f"Will retry after {self.recovery_timeout}s."
            )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions as e:
            self._on_failure()
            raise
    
    def _on_success(self) -> None:
        """Handle successful call."""
        self._failure_count = 0
        self._state = self.CLOSED
        self._lock_time = None
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self.failure_threshold:
            self._state = self.OPEN
            self._lock_time = time.time()
            logger.warning(
                "Circuit breaker tripped. State: OPEN. Failures: %d",
                self._failure_count
            )
    
    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._state = self.CLOSED
        self._failure_count = 0
        self._lock_time = None


# Pre-configured circuit breaker for CACTI connectivity
cacti_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=120.0,
)
