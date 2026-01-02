"""
v18.0 Scraper Utilities
Provides critical security, reliability, and performance improvements
"""
import random
import asyncio
import re
import logging
import signal
from functools import wraps
from typing import Callable, Any, Optional
from datetime import datetime

logger = logging.getLogger("OmniScrape")

# Fix 1.1: User-Agent Rotation Pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.3; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]

def get_random_user_agent() -> str:
    """Returns a random user agent from the pool to avoid bot detection."""
    return random.choice(USER_AGENTS)


# Fix 1.3: Text Sanitization
def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitizes text by removing potentially malicious content.
    
    Args:
        text: Input text to sanitize
        max_length: Optional maximum length to truncate to
    
    Returns:
        Sanitized text string
    """
    if not text:
        return ""
    
    # Remove null bytes (security risk)
    text = text.replace('\x00', '')
    
    # Remove control characters except newline and tab
    text = ''.join(
        char for char in text 
        if char in ('\n', '\t') or not (0 <= ord(char) < 32 or ord(char) == 127)
    )
    
    # Normalize excessive whitespace
    text = re.sub(r' +', ' ', text)  # Multiple spaces to single
    text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines
    
    text = text.strip()
    
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text


# Fix 2.2: Retry Decorator with Exponential Backoff
def retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    log_level: str = "warning"
):
    """
    Retry decorator with exponential backoff for network operations.
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Multiplier for delay between retries
        exceptions: Tuple of exception types to catch and retry
        log_level: Logging level for retry messages
    
    Example:
        @retry(max_attempts=3, exceptions=(TimeoutError, ConnectionError))
        async def fetch_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            delay = 1.0
            last_exception = None
            
            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    attempt += 1
                    
                    if attempt >= max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    log_func = getattr(logger, log_level)
                    log_func(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
            
            # Should never reach here, but for type safety
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


# Fix 2.3 & 8.3: Failure Counter for Circuit Breaker Pattern
class CircuitBreaker:
    """
    Tracks failures and implements circuit breaker pattern.
    Prevents wasting resources on consistently failing operations.
    """
    
    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 300):
        """
        Args:
            failure_threshold: Number of consecutive failures before opening circuit
            timeout_seconds: How long to wait before trying again after circuit opens
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failures = {}
        self.circuit_open_time = {}
    
    def record_failure(self, key: str) -> bool:
        """
        Records a failure for the given key.
        
        Returns:
            True if circuit should be opened (threshold exceeded)
        """
        self.failures[key] = self.failures.get(key, 0) + 1
        
        if self.failures[key] >= self.failure_threshold:
            self.circuit_open_time[key] = datetime.now()
            logger.warning(
                f"Circuit breaker opened for '{key}' after {self.failures[key]} failures. "
                f"Will retry in {self.timeout_seconds}s"
            )
            return True
        
        return False
    
    def record_success(self, key: str):
        """Resets failure counter on successful operation."""
        self.failures[key] = 0
        if key in self.circuit_open_time:
            del self.circuit_open_time[key]
            logger.info(f"Circuit breaker closed for '{key}' after successful operation")
    
    def is_open(self, key: str) -> bool:
        """
        Checks if circuit is open for the given key.
        
        Returns:
            True if circuit is open and timeout hasn't expired
        """
        if key not in self.circuit_open_time:
            return False
        
        open_time = self.circuit_open_time[key]
        elapsed = (datetime.now() - open_time).total_seconds()
        
        if elapsed >= self.timeout_seconds:
            # Timeout expired, allow retry
            del self.circuit_open_time[key]
            self.failures[key] = 0  # Reset to give it a fair chance
            logger.info(f"Circuit breaker timeout expired for '{key}', allowing retry")
            return False
        
        return True
    
    def get_status(self, key: str) -> dict:
        """Returns current status for debugging."""
        return {
            "failures": self.failures.get(key, 0),
            "is_open": self.is_open(key),
            "open_time": self.circuit_open_time.get(key)
        }


# Fix 1.4: Config Validation
def validate_scraper_config(config: dict, scraper_name: str) -> None:
    """
    Validates that scraper config has required fields.
    
    Args:
        config: Configuration dictionary to validate
        scraper_name: Name of the scraper (for error messages)
    
    Raises:
        ValueError: If required fields are missing or invalid
    """
    required_fields = ['base_url', 'card', 'title']
    missing = [field for field in required_fields if field not in config]
    
    if missing:
        raise ValueError(
            f"{scraper_name} config missing required fields: {', '.join(missing)}"
        )
    
    # Validate URL format
    base_url = config['base_url']
    if not isinstance(base_url, str) or not base_url.startswith(('http://', 'https://')):
        raise ValueError(
            f"{scraper_name} base_url must be a string starting with http:// or https://, "
            f"got: {base_url}"
        )
    
    # Validate selectors are non-empty strings
    for field in ['card', 'title']:
        value = config[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"{scraper_name} '{field}' must be a non-empty string, got: {value}"
            )


# Fix 1.2: Rate Limiting
async def rate_limit(min_delay: float = 1.0, max_delay: float = 3.0):
    """
    Adds random delay to prevent rate limiting and avoid bot detection.
    
    Args:
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds
    """
    delay = random.uniform(min_delay, max_delay)
    await asyncio.sleep(delay)


# Fix 2.4: Graceful Shutdown Handler
class GracefulShutdown:
    """
    Handles graceful shutdown on SIGINT/SIGTERM signals.
    Ensures cleanup of browser processes and database connections.
    """
    
    def __init__(self):
        self.shutdown_requested = False
        self.cleanup_callbacks = []
    
    def register_cleanup(self, callback: Callable):
        """Register a cleanup callback to be called on shutdown."""
        self.cleanup_callbacks.append(callback)
    
    def request_shutdown(self):
        """Mark that shutdown has been requested."""
        self.shutdown_requested = True
        logger.warning("Graceful shutdown requested, completing current batch...")
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self.shutdown_requested
    
    async def cleanup(self):
        """Execute all registered cleanup callbacks."""
        logger.info("Executing cleanup callbacks...")
        for callback in self.cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
        logger.info("Cleanup complete")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.request_shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


# Global instance for shutdown handling
shutdown_handler = GracefulShutdown()
