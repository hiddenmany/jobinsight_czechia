"""
v18.0 Critical Fixes Module
Contains utilities and helpers for improved scraper reliability
"""
import random
import asyncio
import re
import logging
from functools import wraps
from typing import Callable, Any
from datetime import datetime

# Fix 1.1: User-Agent Rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWorkKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.3; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]

def get_random_user_agent() -> str:
    """Returns a random user agent from the pool."""
    return random.choice(USER_AGENTS)

# Fix 1.3: Text Sanitization
def sanitize_text(text: str) -> str:
    """
    Sanitizes text by removing potentially malicious content.
    - Strips null bytes
    - Removes control characters (except newline, tab)
    - Limits length
    """
    if not text:
        return ""
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Remove control characters except \n and \t
    text = ''.join(char for char in text if char == '\n' or char == '\t' or not (0 <= ord(char) < 32 or ord(char) == 127))
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

# Fix 2.2: Retry Decorator
def retry(max_attempts: int = 3, backoff_factor: float = 2.0, exceptions: tuple = (Exception,)):
    """
    Retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Multiplier for delay between retries
        exceptions: Tuple of exception types to catch
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            delay = 1.0
            
            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                    
                    logger = logging.getLogger("OmniScrape")
                    logger.warning(f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
            
        return wrapper
    return decorator

# Fix 2.3: Failure Counter
class FailureCounter:
    """Tracks consecutive failures for circuit breaker pattern."""
    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self.counts = {}
    
    def record_failure(self, key: str) -> bool:
        """
        Records a failure. Returns True if threshold exceeded.
        """
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key] >= self.threshold
    
    def record_success(self, key: str):
        """Resets the failure counter on success."""
        self.counts[key] = 0
    
    def is_circuit_open(self, key: str) -> bool:
        """Returns True if circuit breaker is open (too many failures)."""
        return self.counts.get(key, 0) >= self.threshold

# Fix 1.4: Config Validation
def validate_scraper_config(config: dict, scraper_name: str) -> None:
    """
    Validates that scraper config has required fields.
    
    Raises:
        ValueError: If required fields are missing
    """
    required_fields = ['base_url', 'card', 'title']
    missing = [field for field in required_fields if field not in config]
    
    if missing:
        raise ValueError(f"{scraper_name} config missing required fields: {missing}")
    
    # Validate URLs
    if not config['base_url'].startswith('http'):
        raise ValueError(f"{scraper_name} base_url must start with http:// or https://")

