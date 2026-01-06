"""
Unit tests for scraper_utils module.

Tests sanitization, validation, and circuit breaker functionality.
"""

import pytest
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper_utils import sanitize_text, validate_job_data, CircuitBreaker


class TestSanitizeText:
    """Tests for sanitize_text()"""

    def test_removes_null_bytes(self):
        """Should remove null bytes from text"""
        result = sanitize_text("Hello\x00World")
        assert "\x00" not in result

    def test_normalizes_whitespace(self):
        """Should collapse multiple newlines"""
        result = sanitize_text("Line1\n\n\n\nLine2")
        assert result.count("\n") < 4

    def test_strips_leading_trailing(self):
        """Should strip leading/trailing whitespace"""
        result = sanitize_text("   Hello World   ")
        assert result == result.strip()

    def test_handles_empty_string(self):
        """Should handle empty string"""
        result = sanitize_text("")
        assert result == ""

    def test_handles_none(self):
        """Should handle None gracefully"""
        result = sanitize_text(None)
        assert result == "" or result is None


class TestValidateJobData:
    """Tests for validate_job_data()"""

    def test_valid_job(self):
        """Valid job data should return True"""
        assert validate_job_data("Python Developer", "Acme Corp", "https://example.com/job/123")

    def test_missing_title(self):
        """Missing title should return False"""
        assert not validate_job_data("", "Acme Corp", "https://example.com/job/123")

    def test_missing_company(self):
        """Missing company should return False"""
        assert not validate_job_data("Python Developer", "", "https://example.com/job/123")

    def test_missing_link(self):
        """Missing link should return False"""
        assert not validate_job_data("Python Developer", "Acme Corp", "")

    def test_all_missing(self):
        """All fields missing should return False"""
        assert not validate_job_data("", "", "")


class TestCircuitBreaker:
    """Tests for CircuitBreaker class"""

    def test_initially_closed(self):
        """Circuit should be closed initially"""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=60)
        assert not cb.is_open("test_site")

    def test_opens_after_threshold(self):
        """Circuit should open after failure threshold"""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=60)
        
        cb.record_failure("test_site")
        cb.record_failure("test_site")
        assert not cb.is_open("test_site")  # 2 failures, still closed
        
        cb.record_failure("test_site")
        assert cb.is_open("test_site")  # 3 failures, now open

    def test_records_success(self):
        """Recording success should keep circuit closed"""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=60)
        
        cb.record_failure("test_site")
        cb.record_success("test_site")  # Reset failures
        cb.record_failure("test_site")
        cb.record_failure("test_site")
        
        # Should still be closed (only 2 consecutive failures)
        assert not cb.is_open("test_site")

    def test_different_sites_independent(self):
        """Different sites should have independent circuits"""
        cb = CircuitBreaker(failure_threshold=2, timeout_seconds=60)
        
        cb.record_failure("site_a")
        cb.record_failure("site_a")
        
        assert cb.is_open("site_a")
        assert not cb.is_open("site_b")  # site_b is independent
