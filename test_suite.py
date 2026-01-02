import analyzer
import pandas as pd

def test_salary_parsing():
    print("[TEST] Salary Parsing...")
    core = analyzer.IntelligenceCore()
    cases = [
        ("40 000 - 60 000 Kč", 40000, 60000, 50000),  # min, max, avg
        ("od 35.000 CZK", 35000, 35000, 35000),
        ("Not a salary", None, None, None)
    ]
    for input_str, expected_min, expected_max, expected_avg in cases:
        min_sal, max_sal, avg_sal = core._parse_salary(input_str)
        # Handle float/int comparison - both None or approximately equal
        if expected_avg is None:
            assert avg_sal is None, f"Failed case: {input_str} -> avg={avg_sal} (expected None)"
        else:
            assert avg_sal is not None and abs(avg_sal - expected_avg) < 1, f"Failed case: {input_str} -> avg={avg_sal} (expected {expected_avg})"
            assert min_sal is not None and abs(min_sal - expected_min) < 1, f"Failed case: {input_str} -> min={min_sal} (expected {expected_min})"
            assert max_sal is not None and abs(max_sal - expected_max) < 1, f"Failed case: {input_str} -> max={max_sal} (expected {expected_max})"
    print("  OK.")

def test_content_hashing():
    print("[TEST] Content Hashing...")
    row1 = {"title": "Python Dev", "company": "iSTYLE", "description": "Great job with Apple."}
    row2 = {"title": "Python Dev", "company": "iSTYLE", "description": "Great job with Apple."} # Exact
    row3 = {"title": "Python Dev ", "company": "iSTYLE", "description": "Great job with Apple!"} # Whitespace/Punc diff
    
    h1 = analyzer.get_content_hash(row1["title"], row1["company"], row1["description"])
    h2 = analyzer.get_content_hash(row2["title"], row2["company"], row2["description"])
    h3 = analyzer.get_content_hash(row3["title"], row3["company"], row3["description"])
    
    assert h1 == h2, "Strict duplicate failed"
    assert h1 == h3, "Fuzzy duplicate failed (normalized content)"
    print("  OK.")

def test_normalization():
    print("[TEST] Unicode Normalization...")
    input_str = "Praha\u00a04 – Nusle" # Non-breaking space
    expected = "Praha 4 – Nusle"
    result = analyzer.normalize_text(input_str)
    assert result == expected, f"Normalization failed: {result}"
    print("  OK.")

if __name__ == "__main__":
    try:
        test_salary_parsing()
        test_content_hashing()
        test_normalization()
        print("\n[ALL TESTS PASSED] Architecture is sound.")
    except Exception as e:
        print(f"\n[TEST FAILED] {e}")
        exit(1)
