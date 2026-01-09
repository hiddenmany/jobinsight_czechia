import re
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict

import yaml

logger = logging.getLogger('HR-Intel-Parsers')

# --- DYNAMIC CURRENCY RATES (loaded from config) ---
_CURRENCY_RATES: Dict[str, float] = {}

def _load_currency_rates() -> Dict[str, float]:
    """Load currency rates from config/currency_rates.yaml with fallback defaults."""
    global _CURRENCY_RATES
    if _CURRENCY_RATES:
        return _CURRENCY_RATES
    
    config_path = Path(__file__).parent / 'config' / 'currency_rates.yaml'
    defaults = {'EUR': 25.0, 'USD': 23.0, 'GBP': 29.0, 'PLN': 5.8, 'CHF': 26.0}
    
    try:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                _CURRENCY_RATES = data.get('currency_rates', defaults)
                logger.info(f"Loaded currency rates: {_CURRENCY_RATES}")
        else:
            logger.warning(f"Currency config not found at {config_path}, using defaults")
            _CURRENCY_RATES = defaults
    except Exception as e:
        logger.error(f"Failed to load currency rates: {e}, using defaults")
        _CURRENCY_RATES = defaults
    
    return _CURRENCY_RATES

# Compiled regex patterns for performance
SALARY_NUM_PATTERN = re.compile(r"(\d+(?:\.\d+)?)")
THOUSAND_SEP_PATTERN = re.compile(r"(\d)\.(\d{3})")
# Range pattern: handles both integers and decimals (after comma-to-dot conversion)
RANGE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:-|–|—|až)\s*(\d+(?:\.\d+)?)")

# Bonus detection patterns (Czech and English)
BONUS_PATTERNS = [
    r'bonus[ey]?\s*[:=]?\s*(\d+)',           # bonus: 10000, bonusy 5000
    r'prémie\s*[:=]?\s*(\d+)',               # prémie: 10000
    r'(\d+)\s*(?:kč|czk)?\s*bonus',          # 10000 bonus
    r'13\.?\s*plat',                          # 13. plat (13th salary)
    r'14\.?\s*plat',                          # 14. plat (14th salary)
    r'třináctý\s*plat',                       # třináctý plat
    r'čtrnáctý\s*plat',                       # čtrnáctý plat
    r'roční\s*bonus\s*[:=]?\s*(\d+)',        # roční bonus: 50000
    r'annual\s*bonus\s*[:=]?\s*(\d+)',       # annual bonus: 50000
    r'performance\s*bonus\s*[:=]?\s*(\d+)',  # performance bonus
    r'sign[- ]?on\s*bonus\s*[:=]?\s*(\d+)',  # sign-on bonus
]
BONUS_COMPILED = [re.compile(p, re.IGNORECASE) for p in BONUS_PATTERNS]

# Pattern to detect if string mentions bonus without specific amount
BONUS_MENTION_PATTERN = re.compile(
    r'bonus|prémie|13\.?\s*plat|14\.?\s*plat|třináct|čtrnáct|roční odměn',
    re.IGNORECASE
)

class SalaryParser:
    @staticmethod
    def parse(s: str, source: Optional[str] = None) -> Tuple[Optional[int], Optional[int], Optional[float]]:
        """
        Parse salary string and return (min_salary, max_salary, avg_salary).
        FIXED: Prioritizes range patterns to avoid noise from bonuses/years.
        """
        if not s or not isinstance(s, str):
            return None, None, None
            
        original_input = s
        s = s.lower().replace(" ", "").replace(" ", "")
        
        # Handle decimal commas (3,3 -> 3.3) before thousand separator removal
        s = re.sub(r',(\d{1,2})($|[^0-9])', r'.\1\g<2>', s)
        
        # Remove thousand separators (dots)
        s = re.sub(r'(\d)\.(\d{3})', r'\1\2', s)
        
        # Handle 'k' notation (e.g., 80k -> 80000)
        s = re.sub(r'(\d+(?:\.\d+)?)k(?!č)', lambda m: str(int(float(m.group(1)) * 1000)), s)
        
        # Pre-process ranges to ensure both numbers are expanded if 'k' was applied to the end
        # e.g. 45-80000 -> 45000-80000
        range_match = re.search(r'(\d+(?:\.\d+)?)([-–])(\d{4,6})', s)
        if range_match:
            first_val = float(range_match.group(1))
            second_val = float(range_match.group(3))
            if first_val < 1000 and second_val >= 10000:
                s = s.replace(f"{range_match.group(1)}{range_match.group(2)}{range_match.group(3)}", 
                            f"{int(first_val*1000)}{range_match.group(2)}{range_match.group(3)}")

        # --- NEW: PRIMARY RANGE DETECTION ---
        # Prioritize "X - Y" or "X až Y" patterns
        nums = []
        is_range = False
        
        # Re-check for ranges in the cleaned string
        found_range = RANGE_PATTERN.search(s)
        if found_range:
            nums = [float(found_range.group(1)), float(found_range.group(2))]
            is_range = True
        
        # --- UNIT CONVERSION ---
        # Threshold constants (validated against CZ market 2026)
        # - HOURLY_THRESHOLD: Max reasonable hourly rate before assuming it's monthly
        #   Executive consultants can reach 2000-3500 CZK/hour
        # - DAILY_THRESHOLD: Max reasonable daily rate before assuming it's monthly
        #   Senior contractors can reach 15000-25000 CZK/day
        HOURLY_THRESHOLD = 3500  # CZK/hour - covers executive consultants
        DAILY_THRESHOLD = 25000  # CZK/day - covers senior contractors
        MONTHLY_HOURS = 160
        WORKING_DAYS = 22
        
        # Daily rates
        if '/den' in s or '/day' in s or 'denně' in s or 'per day' in s or 'daily' in s:
            if not is_range: nums = [float(n) for n in SALARY_NUM_PATTERN.findall(s)]
            nums = [n * WORKING_DAYS if n <= DAILY_THRESHOLD else n for n in nums]
        # Hourly rates
        elif '/hod' in s or '/h' in s or 'hodinu' in s or 'per hour' in s:
            if not is_range: nums = [float(n) for n in SALARY_NUM_PATTERN.findall(s)]
            nums = [n * MONTHLY_HOURS if n <= HOURLY_THRESHOLD else n for n in nums]
        else:
            if not is_range:
                nums_raw = [float(n) for n in SALARY_NUM_PATTERN.findall(s)]
            else:
                nums_raw = nums  # Use already detected range numbers
            
            # StartupJobs shorthand handling - applies to BOTH ranges and single values
            if source == 'StartupJobs' and "eur" not in s and "€" not in s:
                nums = []
                for n in nums_raw:
                    if n < 300: nums.append(n * 1000)        # 60-80 -> 60k-80k
                    elif n < 2000: nums.append(n * 160)      # 600-900 -> hourly
                    elif n < 15000: nums.append(n * 22)      # 5000-8000 -> daily
                    else: nums.append(n)
            else:
                nums = nums_raw

        # Foreign currency conversion (dynamic rates from config)
        rates = _load_currency_rates()
        if "eur" in s or "€" in s:
            nums = [n * rates.get('EUR', 25.0) for n in nums]
        elif "usd" in s or "$" in s:
            nums = [n * rates.get('USD', 23.0) for n in nums]
        elif "gbp" in s or "£" in s:
            nums = [n * rates.get('GBP', 29.0) for n in nums]
        elif "pln" in s or "zł" in s:
            nums = [n * rates.get('PLN', 5.8) for n in nums]
        elif "chf" in s:
            nums = [n * rates.get('CHF', 26.0) for n in nums]
        
        # Special Case: Unpaid / Negotiable
        if 'unpaid' in s or re.search(r'(^|[^0-9])0(czk|kč)', s):
            return 0, 0, 0
        if 'dohodou' in s or 'negotiable' in s or 'tbd' in s:
            return -1, -1, -1
        
        if not nums:
            return None, None, None
        
        # Final cleanup: if we have multiple numbers and it was a range, only use the first two
        if is_range and len(nums) > 2:
            nums = nums[:2]
        # If it wasn't a range, and we have many numbers, exclude obvious noise (e.g. < 10)
        elif not is_range and len(nums) > 1:
            nums = [n for n in nums if n > 100] # Ignore 5 years, etc.
            if not nums: return None, None, None

        min_sal = int(min(nums))
        max_sal = int(max(nums))
        avg_sal = float(sum(nums) / len(nums))
        
        if avg_sal < 10000 or avg_sal > 1000000:
            logger.debug(f"Suspicious salary detected: {avg_sal} CZK from '{original_input}'")
        
        return min_sal, max_sal, avg_sal

    @staticmethod
    def parse_with_bonus(s: str, source: Optional[str] = None) -> dict:
        """
        Enhanced salary parsing that separates base salary from bonus components.
        
        Returns:
            dict with keys:
                - base_min, base_max, base_avg: Base salary (excluding bonus)
                - bonus_amount: Detected bonus amount (if specific number found)
                - has_bonus: True if any bonus mention detected
                - has_13th_salary: True if 13th/14th month salary mentioned
                - raw_input: Original input string
        """
        result = {
            'base_min': None,
            'base_max': None,
            'base_avg': None,
            'bonus_amount': None,
            'has_bonus': False,
            'has_13th_salary': False,
            'raw_input': s
        }
        
        if not s or not isinstance(s, str):
            return result
        
        s_lower = s.lower()
        
        # Check for negative context (no bonus)
        no_bonus_pattern = re.search(r'bez\s*bonus|no\s*bonus|without\s*bonus|není\s*bonus', s_lower)
        
        # Detect bonus mentions (only if not negated)
        if not no_bonus_pattern:
            result['has_bonus'] = bool(BONUS_MENTION_PATTERN.search(s_lower))
            result['has_13th_salary'] = bool(re.search(r'13\.?\s*plat|14\.?\s*plat|třináct|čtrnáct', s_lower))
        
        # Try to extract specific bonus amount
        for pattern in BONUS_COMPILED:
            match = pattern.search(s_lower)
            if match and match.groups():
                # Extract the captured number group
                for group in match.groups():
                    if group and group.isdigit():
                        bonus_val = int(group)
                        # Apply k-notation if small number
                        if bonus_val < 300:
                            bonus_val *= 1000
                        result['bonus_amount'] = bonus_val
                        break
            if result['bonus_amount']:
                break
        
        # Parse base salary using existing method
        min_sal, max_sal, avg_sal = SalaryParser.parse(s, source)
        
        # If we found a specific bonus amount and it's in the parsed numbers,
        # try to separate it from base salary
        if result['bonus_amount'] and avg_sal:
            # If the bonus amount is significantly different from avg, 
            # it might have been included - subtract it
            if result['bonus_amount'] < avg_sal * 0.5:
                # Bonus is less than half of avg, likely a separate component
                # Don't adjust base - the parse already handles ranges correctly
                pass
        
        result['base_min'] = min_sal
        result['base_max'] = max_sal
        result['base_avg'] = avg_sal
        
        if result['has_bonus']:
            logger.debug(f"Bonus detected in: '{s}' -> bonus={result['bonus_amount']}, has_13th={result['has_13th_salary']}")
        
        return result

