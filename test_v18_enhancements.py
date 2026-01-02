"""
v18.0 Enhancement Tests
Tests new security, reliability, and bug fixes
"""
import analyzer
import scraper_utils
import asyncio

def test_user_agent_rotation():
    """Test that UA rotation provides diverse agents."""
    print("[TEST] User-Agent Rotation...")
    uas = [scraper_utils.get_random_user_agent() for _ in range(10)]
    unique_uas = len(set(uas))
    assert unique_uas >= 3, f"Expected at least 3 different UAs, got {unique_uas}"
    print(f"  OK: Generated {unique_uas} unique UAs from 10 calls")

def test_text_sanitization():
    """Test text sanitization removes malicious content."""
    print("[TEST] Text Sanitization...")
    
    # Test null byte removal
    dirty = "Safe text\x00malicious"
    clean = scraper_utils.sanitize_text(dirty)
    assert '\x00' not in clean
    
    # Test control character removal
    dirty = "Text\x01\x02\x03with\x1fcontrol\x1bchars"
    clean = scraper_utils.sanitize_text(dirty)
    assert len([c for c in clean if ord(c) < 32]) == 0
    
    # Test length limiting
    long_text = "A" * 1000
    clean = scraper_utils.sanitize_text(long_text, max_length=100)
    assert len(clean) == 100
    
    print("  OK: Sanitization working correctly")

def test_circuit_breaker():
    """Test circuit breaker opens after threshold."""
    print("[TEST] Circuit Breaker...")
    
    cb = scraper_utils.CircuitBreaker(failure_threshold=3, timeout_seconds=1)
    
    # Record failures
    assert not cb.is_open('test_site')
    cb.record_failure('test_site')
    assert not cb.is_open('test_site')
    cb.record_failure('test_site')
    assert not cb.is_open('test_site')
    cb.record_failure('test_site')
    assert cb.is_open('test_site'), "Circuit should be open after 3 failures"
    
    # Test timeout
    import time
    time.sleep(1.1)
    assert not cb.is_open('test_site'), "Circuit should close after timeout"
    
    # Test success reset
    cb.record_failure('test_site2')
    cb.record_success('test_site2')
    status = cb.get_status('test_site2')
    assert status['failures'] == 0
    
    print("  OK: Circuit breaker logic correct")

def test_config_validation():
    """Test config validation catches errors."""
    print("[TEST] Config Validation...")
    
    # Valid config
    try:
        scraper_utils.validate_scraper_config({
            'base_url': 'https://example.com',
            'card': '.card',
            'title': '.title'
        }, 'TestScraper')
        print("  OK: Valid config accepted")
    except:
        assert False, "Valid config should not raise error"
    
    # Missing field
    try:
        scraper_utils.validate_scraper_config({
            'base_url': 'https://example.com',
            'card': '.card'
        }, 'TestScraper')
        assert False, "Should have raised ValueError for missing 'title'"
    except ValueError as e:
        assert 'title' in str(e)
        print("  OK: Missing field detected")
    
    # Invalid URL
    try:
        scraper_utils.validate_scraper_config({
            'base_url': 'not-a-url',
            'card': '.card',
            'title': '.title'
        }, 'TestScraper')
        assert False, "Should have raised ValueError for invalid URL"
    except ValueError as e:
        assert 'http' in str(e).lower()
        print("  OK: Invalid URL detected")

async def test_rate_limiting():
    """Test rate limiting adds appropriate delays."""
    print("[TEST] Rate Limiting...")
    import time
    
    start = time.time()
    await scraper_utils.rate_limit(0.1, 0.2)
    elapsed = time.time() - start
    
    assert 0.09 <= elapsed <= 0.25, f"Expected 0.1-0.2s delay, got {elapsed:.3f}s"
    print(f"  OK: Rate limiting working ({elapsed:.3f}s delay)")

async def test_retry_decorator():
    """Test retry mechanism."""
    print("[TEST] Retry Decorator...")
    
    attempt_count = [0]
    
    @scraper_utils.retry(max_attempts=3, exceptions=(ValueError,))
    async def failing_function():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise ValueError("Temporary failure")
        return "success"
    
    result = await failing_function()
    assert result == "success"
    assert attempt_count[0] == 3, f"Expected 3 attempts, got {attempt_count[0]}"
    print(f"  OK: Retry succeeded after {attempt_count[0]} attempts")

def test_compiled_regex_performance():
    """Test that compiled patterns work correctly."""
    print("[TEST] Compiled Regex Patterns...")
    
    import re
    # Test analyzer patterns
    text = "100.000 to 150.000"
    result = analyzer.THOUSAND_SEP_PATTERN.sub(r"\1\2", text)
    assert "100000" in result
    print("  OK: Thousand separator pattern working")
    
    # Test salary pattern
    from scraper import SALARY_PATTERN
    text = "40 000 – 60 000 Kč"
    match = SALARY_PATTERN.search(text)
    assert match is not None
    print("  OK: Salary pattern working")

if __name__ == "__main__":
    print("=" * 70)
    print("v18.0 ENHANCEMENT TEST SUITE")
    print("=" * 70)
    print()
    
    try:
        test_user_agent_rotation()
        test_text_sanitization()
        test_circuit_breaker()
        test_config_validation()
        asyncio.run(test_rate_limiting())
        asyncio.run(test_retry_decorator())
        test_compiled_regex_performance()
        
        print()
        print("=" * 70)
        print("[SUCCESS] ALL v18.0 ENHANCEMENT TESTS PASSED")
        print("=" * 70)
    except Exception as e:
        print()
        print(f"[FAILED] Test error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
