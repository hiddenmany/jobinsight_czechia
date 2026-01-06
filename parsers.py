import re
import logging

logger = logging.getLogger('HR-Intel-Parsers')

# Compiled regex patterns for performance
SALARY_DIGITS_PATTERN = re.compile(r"(\d+)")
THOUSAND_SEP_PATTERN = re.compile(r"(\d)\.(\d{3})")

class SalaryParser:
    @staticmethod
    def parse(s: str, source: str = None) -> tuple:
        """
        Parse salary string and return (min_salary, max_salary, avg_salary).

        Args:
            s: Salary string to parse
            source: Job source (e.g., "StartupJobs") for context-aware parsing

        Returns:
            tuple: (min, max, avg) salary values, or (None, None, None) if parsing fails
        """
        if not s or not isinstance(s, str):
            return None, None, None
            
        s = s.lower().replace(" ", "").replace(" ", "")
        s = re.sub(r'(\d)\.(\d{3})', r'\1\2', s)  # Remove thousand separators only
        
        # Globally handle 'k' notation (e.g., 80k -> 80000) for ALL sources
        # This fixes the bug where "80k" was discarded because 80 < 1000
        # Exclude 'k' if followed by 'č' (e.g. 50000kč) to avoid double expansion
        s = re.sub(r'(\d+)k(?!č)', r'\g<1>000', s)

        # Detect and convert hourly rates to monthly (160 hours/month standard)
        if '/hod' in s or '/h' in s or 'hodinu' in s or 'per hour' in s:
            nums_raw = [int(n) for n in SALARY_DIGITS_PATTERN.findall(s)]
            nums = [n * 160 if n < 1000 else n for n in nums_raw]  # Convert hourly to monthly
        else:
            nums_raw = [int(n) for n in SALARY_DIGITS_PATTERN.findall(s)]
            # StartupJobs often uses "600-900 Kč" to mean "600k-900k"
            if source == 'StartupJobs':
                nums = [n * 1000 if n < 1000 else n for n in nums_raw]
            else:
                nums = nums_raw
        
        # Handle EUR conversion to CZK (approximate rate)
        if "eur" in s or "€" in s:
            nums = [n * 25 for n in nums]
        elif "usd" in s or "$" in s:
            nums = [n * 23 for n in nums]
        
        # Distinguish between NULL (missing), 0 (unpaid), and negotiable
        original_text = s  # Keep original for special case detection
        
        # Check for unpaid internships
        # Use regex to avoid matching "0kč" inside "50000kč"
        if 'unpaid' in original_text or re.search(r'(^|[^0-9])0(czk|kč)', original_text):
            return 0, 0, 0  # Explicitly 0 for unpaid positions
        
        # Check for negotiable salary
        if 'dohodou' in original_text or 'negotiable' in original_text or 'tbd' in original_text:
            return -1, -1, -1  # Special marker for "to be discussed"
        
        if not nums:
            return None, None, None  # NULL for missing salary data
        
        # Salary validation: Flag suspiciously low or high values
        min_sal = min(nums)
        max_sal = max(nums)
        avg_sal = sum(nums) / len(nums)
        
        # Sanity check: Monthly salaries in Czech Republic
        if avg_sal < 15000 or avg_sal > 500000:
            logger.debug(f"Suspicious salary detected: {avg_sal} CZK from '{original_text}'")
        
        return min_sal, max_sal, avg_sal
