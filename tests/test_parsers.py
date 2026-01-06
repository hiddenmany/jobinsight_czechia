import pytest
from parsers import SalaryParser

@pytest.mark.parametrize("input_str, source, expected", [
    # Standard formats
    ("40 000 - 60 000 Kč", None, (40000, 60000, 50000)),
    ("od 35.000 CZK", None, (35000, 35000, 35000)),
    ("50 000 Kč", None, (50000, 50000, 50000)),
    
    # StartupJobs multiplier logic
    ("60-80 000 Kč", "StartupJobs", (60000, 80000, 70000)),
    
    # k-notation fix (Global)
    ("80k - 100k", "LinkedIn", (80000, 100000, 90000)),
    ("50k", None, (50000, 50000, 50000)),

    # Hourly rates
    ("300 Kč/hod", None, (48000, 48000, 48000)), # 300 * 160
    
    # Currency conversion
    ("2000 EUR", None, (50000, 50000, 50000)), # 2000 * 25
    
    # WTTJ salary (non-k format, should pass through)
    ("45 000 Kč", "WTTJ", (45000, 45000, 45000)),
    # Edge case: small numbers that aren't salaries should still parse
    ("600 Kč/hod", None, (96000, 96000, 96000)),  # 600 * 160 hourly

    # Special cases
    ("Unpaid internship", None, (0, 0, 0)),
    ("Mzda dohodou", None, (-1, -1, -1)),
    (None, None, (None, None, None)),
    ("Invalid salary", None, (None, None, None)),
])
def test_salary_parsing(input_str, source, expected):
    min_sal, max_sal, avg_sal = SalaryParser.parse(input_str, source)
    
    # Helper to compare with tolerance for floats if needed, though mostly ints here
    def is_close(a, b):
        if a is None and b is None: return True
        if a is None or b is None: return False
        return abs(a - b) < 1

    assert is_close(min_sal, expected[0]), f"Min salary mismatch for {input_str}"
    assert is_close(max_sal, expected[1]), f"Max salary mismatch for {input_str}"
    assert is_close(avg_sal, expected[2]), f"Avg salary mismatch for {input_str}"
