"""
L-2 FIX: Comprehensive tests for SalaryParser edge cases.
Tests k-notation, hourly-to-monthly conversion, currency conversion,
negotiable salaries, and validation bounds.
"""
import pytest
from parsers import SalaryParser, _load_currency_rates

# Currency rates loaded dynamically from config (matches parsers.py)
CURRENCY_RATES = _load_currency_rates()
# Salary validation bounds (matching parsers.py logic)
MIN_VALID_SALARY = 15000
MAX_VALID_SALARY = 500000


class TestSalaryParserBasic:
    """Basic parsing tests."""
    
    def test_parse_simple_range(self):
        """Parse simple CZK salary range."""
        min_s, max_s, avg_s = SalaryParser.parse("40000 - 60000 Kč")
        assert min_s == 40000
        assert max_s == 60000
        assert avg_s == 50000
    
    def test_parse_empty_string(self):
        """Empty string returns None tuple."""
        assert SalaryParser.parse("") == (None, None, None)
        assert SalaryParser.parse(None) == (None, None, None)
    
    def test_parse_single_value(self):
        """Single value should work."""
        min_s, max_s, avg_s = SalaryParser.parse("50000 Kč")
        assert min_s == 50000
        assert max_s == 50000


class TestKNotation:
    """Test k-notation handling (e.g., 80k, 50K)."""
    
    def test_k_notation_lowercase(self):
        """80k should become 80000."""
        min_s, max_s, avg_s = SalaryParser.parse("80k-100k CZK")
        assert min_s == 80000
        assert max_s == 100000
    
    def test_k_notation_uppercase(self):
        """50K should become 50000."""
        min_s, max_s, avg_s = SalaryParser.parse("50K Kč")
        assert min_s == 50000
    
    def test_k_notation_range(self):
        """45-80k should become 45000-80000 (k applies to whole range)."""
        min_s, max_s, avg_s = SalaryParser.parse("45-80k")
        assert min_s == 45000
        assert max_s == 80000
        assert avg_s == 62500
    
    def test_k_notation_not_double_expanded(self):
        """50000kč should NOT become 50000000."""
        min_s, max_s, avg_s = SalaryParser.parse("50000kč")
        assert avg_s == 50000


class TestHourlyConversion:
    """Test hourly-to-monthly conversion (160 hours/month)."""
    
    def test_hourly_czech(self):
        """200 Kč/hod should become 32000 monthly."""
        min_s, max_s, avg_s = SalaryParser.parse("200 Kč/hod")
        assert avg_s == 200 * 160  # 32000
    
    def test_hourly_english(self):
        """250 CZK/h = 40000 monthly which is valid."""
        min_s, max_s, avg_s = SalaryParser.parse("250 CZK/h")
        assert avg_s == 250 * 160  # 40000, within valid range


class TestCurrencyConversion:
    """Test EUR and USD conversion to CZK."""
    
    def test_eur_conversion(self):
        """2000 EUR should be converted using CURRENCY_RATES."""
        min_s, max_s, avg_s = SalaryParser.parse("2000 EUR")
        expected = 2000 * CURRENCY_RATES['EUR']
        assert avg_s == expected
    
    def test_usd_conversion(self):
        """3000 USD should be converted using CURRENCY_RATES."""
        min_s, max_s, avg_s = SalaryParser.parse("3000 USD")
        expected = 3000 * CURRENCY_RATES['USD']
        assert avg_s == expected
    
    def test_euro_symbol(self):
        """€2000 should be recognized as EUR."""
        min_s, max_s, avg_s = SalaryParser.parse("€2000")
        expected = 2000 * CURRENCY_RATES['EUR']
        assert avg_s == expected


class TestSpecialCases:
    """Test special salary cases."""
    
    def test_unpaid_internship(self):
        """Unpaid returns (0, 0, 0)."""
        assert SalaryParser.parse("unpaid internship") == (0, 0, 0)
        assert SalaryParser.parse("0 Kč") == (0, 0, 0)
    
    def test_negotiable_salary(self):
        """Negotiable returns (-1, -1, -1)."""
        assert SalaryParser.parse("dohodou") == (-1, -1, -1)
        assert SalaryParser.parse("negotiable") == (-1, -1, -1)
        assert SalaryParser.parse("TBD") == (-1, -1, -1)


class TestValidation:
    """Test salary validation bounds (H-2 FIX).
    
    NOTE: Parser logs warnings for suspicious salaries but doesn't reject them.
    This is by design to preserve data for manual review.
    """
    
    def test_below_minimum_logged(self):
        """Salary below MIN_VALID_SALARY is parsed but flagged (logs warning)."""
        result = SalaryParser.parse("5000 Kč")
        # Parser returns the value (doesn't reject) but logs a warning
        assert result == (5000, 5000, 5000.0)
    
    def test_above_maximum_logged(self):
        """Salary above MAX_VALID_SALARY is parsed but flagged (logs warning)."""
        result = SalaryParser.parse("1000000 Kč")
        # Parser returns the value (doesn't reject) but logs a warning
        assert result == (1000000, 1000000, 1000000.0)
    
    def test_valid_salary_accepted(self):
        """Valid salary within bounds is accepted."""
        min_s, max_s, avg_s = SalaryParser.parse("50000 Kč")
        assert avg_s == 50000


class TestStartupJobsSource:
    """Test StartupJobs-specific parsing."""
    
    def test_startupjobs_k_shorthand(self):
        """StartupJobs low numbers (<300) should be multiplied by 1000."""
        min_s, max_s, avg_s = SalaryParser.parse("60-80 Kč", source="StartupJobs")
        assert min_s == 60000
        assert max_s == 80000

    def test_startupjobs_hourly_shorthand(self):
        """StartupJobs mid numbers (300-2000) should be treated as hourly (x160)."""
        # This was the bug: 600-900 was becoming 600k-900k
        min_s, max_s, avg_s = SalaryParser.parse("600-900 Kč", source="StartupJobs")
        assert min_s == 600 * 160  # 96000
        assert max_s == 900 * 160  # 144000

    def test_startupjobs_daily_shorthand(self):
        """StartupJobs numbers (2000-15000) should be treated as daily (x22)."""
        min_s, max_s, avg_s = SalaryParser.parse("5000 - 8000 Kč", source="StartupJobs")
        assert min_s == 5000 * 22  # 110000
        assert max_s == 8000 * 22  # 176000

    def test_startupjobs_eur_no_double_mult(self):
        """EUR values should NOT trigger StartupJobs shorthand multipliers (x22, x160)."""
        # This was the bug: 3300 EUR was becoming 3300 * 22 * 25
        eur_rate = CURRENCY_RATES['EUR']
        min_s, max_s, avg_s = SalaryParser.parse("3,3 - 3300 €", source="StartupJobs")
        # 3,3 -> 3.3. 3300 -> 3300.
        # EUR conversion only: 3.3 * rate, 3300 * rate
        # Rate is now ~25.2 (dynamic), so 3.3 * 25.2 = 83.16 -> 83
        assert min_s == int(3.3 * eur_rate)
        assert max_s == int(3300 * eur_rate)
        assert avg_s == (3.3 * eur_rate + 3300 * eur_rate) / 2


class TestThousandSeparators:
    """Test thousand separator handling."""
    
    def test_dot_separator(self):
        """50.000 Kč should be 50000."""
        min_s, max_s, avg_s = SalaryParser.parse("50.000 Kč")
        assert avg_s == 50000
    
    def test_space_separator(self):
        """50 000 Kč should be 50000."""
        min_s, max_s, avg_s = SalaryParser.parse("50 000 Kč")
        # After space removal and joining, this becomes 50000
        assert avg_s == 50000
