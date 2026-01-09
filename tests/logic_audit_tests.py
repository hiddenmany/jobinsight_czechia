import unittest
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from classifiers import JobClassifier
from parsers import SalaryParser

class LogicAuditTest(unittest.TestCase):
    
    # --- KEYWORD MATCHING TESTS ---
    
    def test_case_insensitivity(self):
        """Verify matching is case-insensitive."""
        self.assertEqual(JobClassifier.classify_role("DEVELOPER"), "Developer")
        self.assertEqual(JobClassifier.classify_role("developer"), "Developer")
        self.assertEqual(JobClassifier.classify_role("dEvElOpEr"), "Developer")

    def test_exact_word_matching(self):
        """Verify short keywords use word boundaries (no partial matches like 'pitch')."""
        # 'it' is in taxonomy, but 'pitch' contains 'it'. Should be 'Other' if no other match.
        self.assertEqual(JobClassifier.classify_role("Great pitch for sales"), "Sales")
        # 'it' as a word should match Developer if tech context is present
        self.assertEqual(JobClassifier.classify_role("IT Specialist", "software development"), "Developer")

    def test_substring_matches(self):
        """Verify longer keywords allow substring/partial matches."""
        # 'logistik' should match 'Logistics'
        self.assertEqual(JobClassifier.classify_role("Logistika a doprava"), "Logistics")
        # 'účetní' should match 'Finance'
        self.assertEqual(JobClassifier.classify_role("Mzdová účetní"), "Finance")

    def test_exclusion_rule_overrides(self):
        """Verify specific exclusion rules (e.g., Grafik směn)."""
        # 'grafik' is Designer, but 'grafik směn' is 'Management' or 'Other' (depending on context)
        # In current logic, 'grafik' + 'směn' returns False in smart_match, falling through to 'Manufacturing' or 'Other'
        result = JobClassifier.classify_role("Grafik směn ve výrobě")
        self.assertNotEqual(result, "Designer")
        self.assertEqual(result, "Manufacturing")

    # --- CATEGORIZATION LOGIC TESTS ---

    def test_top_level_overrides(self):
        """Verify priority overrides like Legal and Education."""
        self.assertEqual(JobClassifier.classify_role("PhD Student", "doing python"), "Education")
        self.assertEqual(JobClassifier.classify_role("Právník / Legal Counsel"), "Legal")

    def test_refinement_layer(self):
        """Verify post-classification refinement (Sanity Checks)."""
        # Real Estate Developer -> Construction
        self.assertEqual(JobClassifier.classify_role("Developer", "development nemovitostí, real estate"), "Construction")
        # IT Admin -> Developer
        self.assertEqual(JobClassifier.classify_role("IT Administrátor"), "Developer")
        # HVAC -> General Engineering
        self.assertEqual(JobClassifier.classify_role("Projektant HVAC", "klimatizace a chlazení"), "General Engineering")

    # --- PARSING LOGIC TESTS ---

    def test_salary_ranges(self):
        """Verify range detection handles various separators and formats."""
        # Standard range
        self.assertEqual(SalaryParser.parse("50 000 - 70 000 Kč")[2], 60000)
        # Mixed format with dots
        self.assertEqual(SalaryParser.parse("50.000 až 70.000")[2], 60000)
        # Decimals
        self.assertEqual(SalaryParser.parse("45,5 - 55,5 k")[2], 50500)

    def test_startup_jobs_shorthand(self):
        """Verify StartupJobs specific shorthand logic (60-80 -> 60k-80k)."""
        self.assertEqual(SalaryParser.parse("60 - 80", source="StartupJobs")[2], 70000)

    def test_threshold_boundaries(self):
        """Verify executive rate thresholds (3500/hr, 25000/day)."""
        # Hourly threshold (3500)
        self.assertEqual(SalaryParser.parse("3500 Kč/hod")[2], 3500 * 160)
        # Just above threshold -> interpreted as monthly
        self.assertEqual(SalaryParser.parse("4000 Kč/hod")[2], 4000) 
        
        # Daily threshold (25000)
        self.assertEqual(SalaryParser.parse("25000 Kč/den")[2], 25000 * 22)
        # Just above threshold -> monthly
        self.assertEqual(SalaryParser.parse("30000 Kč/den")[2], 30000)

    def test_bonus_negative_context(self):
        """Verify 'bez bonusu' is not detected as having a bonus."""
        result = SalaryParser.parse_with_bonus("70 000 Kč bez bonusů")
        self.assertFalse(result['has_bonus'])
        
        result = SalaryParser.parse_with_bonus("70 000 Kč + roční bonusy")
        self.assertTrue(result['has_bonus'])

if __name__ == "__main__":
    unittest.main()
