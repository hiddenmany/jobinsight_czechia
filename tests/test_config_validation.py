"""
Stage 4: Config Validation Tests.

Tests the scraper configuration validation including:
- Required field detection
- URL format validation  
- Selector format validation
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper_utils import validate_scraper_config


class TestConfigValidation:
    """Tests for validate_scraper_config()."""

    def test_valid_config_accepted(self):
        """Complete valid config should not raise."""
        config = {
            'base_url': 'https://example.com/jobs',
            'card': '.job-card',
            'title': '.job-title'
        }
        # Should not raise
        validate_scraper_config(config, 'TestScraper')

    def test_missing_base_url_rejected(self):
        """Config without base_url should raise ValueError."""
        config = {
            'card': '.job-card',
            'title': '.job-title'
        }
        with pytest.raises(ValueError) as excinfo:
            validate_scraper_config(config, 'TestScraper')
        assert 'base_url' in str(excinfo.value)

    def test_missing_card_rejected(self):
        """Config without card selector should raise ValueError."""
        config = {
            'base_url': 'https://example.com/jobs',
            'title': '.job-title'
        }
        with pytest.raises(ValueError) as excinfo:
            validate_scraper_config(config, 'TestScraper')
        assert 'card' in str(excinfo.value)

    def test_missing_title_rejected(self):
        """Config without title selector should raise ValueError."""
        config = {
            'base_url': 'https://example.com/jobs',
            'card': '.job-card'
        }
        with pytest.raises(ValueError) as excinfo:
            validate_scraper_config(config, 'TestScraper')
        assert 'title' in str(excinfo.value)

    def test_invalid_url_format_rejected(self):
        """Config with invalid URL should raise ValueError."""
        config = {
            'base_url': 'not-a-valid-url',
            'card': '.job-card',
            'title': '.job-title'
        }
        with pytest.raises(ValueError) as excinfo:
            validate_scraper_config(config, 'TestScraper')
        assert 'http' in str(excinfo.value).lower()

    def test_http_url_accepted(self):
        """HTTP URL should be accepted (not just HTTPS)."""
        config = {
            'base_url': 'http://example.com/jobs',
            'card': '.job-card',
            'title': '.job-title'
        }
        # Should not raise
        validate_scraper_config(config, 'TestScraper')

    def test_empty_card_selector_rejected(self):
        """Empty card selector should raise ValueError."""
        config = {
            'base_url': 'https://example.com/jobs',
            'card': '',
            'title': '.job-title'
        }
        with pytest.raises(ValueError) as excinfo:
            validate_scraper_config(config, 'TestScraper')
        assert 'card' in str(excinfo.value)

    def test_whitespace_only_selector_rejected(self):
        """Whitespace-only selector should raise ValueError."""
        config = {
            'base_url': 'https://example.com/jobs',
            'card': '.job-card',
            'title': '   '
        }
        with pytest.raises(ValueError) as excinfo:
            validate_scraper_config(config, 'TestScraper')
        assert 'title' in str(excinfo.value)

    def test_scraper_name_in_error_message(self):
        """Error message should include scraper name for debugging."""
        config = {
            'base_url': 'invalid',
            'card': '.job-card',
            'title': '.job-title'
        }
        with pytest.raises(ValueError) as excinfo:
            validate_scraper_config(config, 'MyCustomScraper')
        assert 'MyCustomScraper' in str(excinfo.value)

    def test_extra_fields_accepted(self):
        """Config with extra optional fields should be accepted."""
        config = {
            'base_url': 'https://example.com/jobs',
            'card': '.job-card',
            'title': '.job-title',
            'salary': '.salary',
            'company': '.company-name',
            'first_page_url': 'https://example.com/jobs/page/1',
            'domain': 'https://example.com'
        }
        # Should not raise
        validate_scraper_config(config, 'TestScraper')
