import pytest
from tools.whitelist_discovery import format_report

def test_format_report_structure():
    """Test that report contains expected sections."""
    results = {
        "kubernetes": "Tech",
        "driver": "Non-Tech",
        "random": "Unrelated"
    }
    added_terms = ["kubernetes"]
    
    report = format_report(results, added_terms)
    
    assert "# Whitelist Auto-update Report" in report
    assert "## Automatically Added Terms" in report
    assert "- kubernetes" in report
    assert "## Review Candidates" in report
    assert "driver" in report
    # We might not show Unrelated, or maybe we do.
    # The spec says "Flagged candidates (Medium/Low Confidence) for manual review."
    # So probably "Non-Tech" and maybe "Unrelated" if ambiguous.
    # Let's check for "driver" at least.
