import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta
from collections import Counter
import os
import re
import hashlib
import unicodedata
import duckdb
import yaml
from dataclasses import dataclass
from typing import Optional

# New module imports
from parsers import SalaryParser, THOUSAND_SEP_PATTERN
from classifiers import JobClassifier
from settings import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('HR-Intel-Analyzer')

# --- ARCHITECTURAL CONSTANTS (now using centralized Settings) ---
DB_PATH = str(settings.get_db_path())  # Keep as string for duckdb compatibility
TAXONOMY_PATH = str(settings.TAXONOMY_PATH)

def load_taxonomy():
    with open(TAXONOMY_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

TAXONOMY = load_taxonomy()

# --- PRE-COMPILED REGEX PATTERNS (Performance fix: compile once at module load) ---
def _build_word_boundary_pattern(keywords: list) -> re.Pattern:
    """Build a compiled regex pattern with word boundaries for keyword matching."""
    if not keywords:
        return None
    escaped = [re.escape(k) for k in keywords]
    return re.compile(r'\b(' + '|'.join(escaped) + r')\b', re.IGNORECASE)

# Compile patterns from taxonomy at module load
_TECH_KEYWORDS = set(TAXONOMY.get('tech_stack', {}).get('modern', []) + TAXONOMY.get('tech_stack', {}).get('legacy', []))
_TECH_PATTERN = _build_word_boundary_pattern(list(_TECH_KEYWORDS))
_TOXICITY_PATTERN = _build_word_boundary_pattern(TAXONOMY.get('toxicity', {}).get('red_flags', []))
_LEGACY_PATTERN = _build_word_boundary_pattern(TAXONOMY.get('tech_stack', {}).get('legacy', []))
_MODERN_PATTERN = _build_word_boundary_pattern(TAXONOMY.get('tech_stack', {}).get('modern', []))

# Benefit display names (shared by get_benefits_analysis and get_trending_benefits)
BENEFIT_DISPLAY_NAMES = {
    'meal_vouchers': 'Meal Vouchers',
    'fitness': 'Fitness/MultiSport',
    'education': 'Education Budget',
    'equipment': 'Home Office Equipment',
    'stock_equity': 'Stock Options/Equity',
    'bonuses': 'Performance Bonuses',
    'extra_salary': '13th/14th Salary',
    'sick_days': 'Paid Sick Days',
    'extra_vacation': 'Extra Vacation Days',
    'wellness': 'Wellness Programs',
    'parental': 'Parental Benefits',
    'pension': 'Pension Contribution',
    'cafeteria': 'Flexible Benefits (Cafeteria)'
}

@dataclass
class JobSignal:
    """Strict schema for a market signal to prevent typos."""
    title: str
    company: str
    link: str
    source: str
    salary: Optional[str] = None
    description: str = ""
    benefits: str = ""
    location: str = "Czechia"


def normalize_text(text: str) -> str:
    """Normalize text by removing Unicode variations and thousand separators."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    # Remove dots used as thousand separators, standardizing digits (using compiled pattern)
    text = THOUSAND_SEP_PATTERN.sub(r"\1\2", text)
    return text.strip()


def get_content_hash(title: str, company: str, description: str, city: str = "", link: str = "") -> str:
    """Generate a unique hash for content deduplication using SHA256.
    
    Enhanced to handle "Remote" location collisions by:
    1. Using more description content for Remote jobs
    2. Including link as fallback differentiator
    3. Normalizing generic location values
    """
    # Normalize city - treat generic values as needing more differentiation
    city_normalized = (city or "").lower().strip()
    generic_locations = ['remote', 'cz', 'czechia', 'česká republika', 'anywhere', 'home office', '']
    
    # For generic/remote locations, use more content to differentiate
    if city_normalized in generic_locations:
        # Use more of the description (750 chars) and include link suffix
        desc_content = str(description)[:750]
        link_suffix = link[-50:] if link else ""  # Last 50 chars of URL often contain unique ID
        raw = f"{title}{company}{desc_content}{link_suffix}".lower()
    else:
        # Standard hash for jobs with specific locations
        raw = f"{title}{company}{city}{str(description)[:500]}".lower()
    
    clean = re.sub(r"\W+", "", raw)
    return hashlib.sha256(clean.encode()).hexdigest()


class SemanticEngine:
    """Simulates AI logic using high-fidelity keyword weighting (NER Lite)."""

    @staticmethod
    def is_tech_relevant(title: str, description: str) -> bool:
        """Filters out non-tech signals to keep the report focused.
        Uses pre-compiled regex for performance.
        """
        if not _TECH_PATTERN:
            return False
        text = f"{title} {description}"
        return bool(_TECH_PATTERN.search(text))

    @staticmethod
    def analyze_toxicity(description: str) -> int:
        """Detects toxic red flags in JDs. Returns score 0-100.
        Uses pre-compiled regex for performance.
        """
        if not _TOXICITY_PATTERN or not description:
            return 0
        matches = _TOXICITY_PATTERN.findall(description)
        return min(len(matches) * 30, 100)

    @staticmethod
    def analyze_tech_lag(description: str) -> str:
        """Calculates technological obsolescence score. Returns 'Modern', 'Stable', or 'Dinosaur'.
        Uses pre-compiled regex for performance.
        """
        if not description:
            return "Stable"
        
        legacy_hit = len(_LEGACY_PATTERN.findall(description)) if _LEGACY_PATTERN else 0
        modern_hit = len(_MODERN_PATTERN.findall(description)) if _MODERN_PATTERN else 0

        if legacy_hit > modern_hit:
            return "Dinosaur"
        if modern_hit > legacy_hit:
            return "Modern"
        return "Stable"


class IntelligenceCore:
    """The central stateful data brain using DuckDB."""

    def __init__(self, read_only=False):
        settings.ensure_dirs()  # Create data/config/public dirs if needed
        self.con = duckdb.connect(DB_PATH, read_only=read_only)
        self._init_db()
        self._df_cache = None  # Lazy loading cache
        self._cache_timestamp = None

    def _init_db(self):
        # Only create table if not read_only
        try:
            self.con.execute(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    hash TEXT PRIMARY KEY,
                    title TEXT,
                    company TEXT,
                    salary_raw TEXT,
                    avg_salary DOUBLE,
                    description TEXT,
                    benefits TEXT,
                    link TEXT,
                    source TEXT,
                    city TEXT,
                    region TEXT DEFAULT 'Unknown',
                    scraped_at TIMESTAMP,
                    toxicity_score INTEGER,
                    tech_status TEXT,
                    last_seen_at TIMESTAMP,
                    role_type TEXT DEFAULT 'Unknown',
                    seniority_level TEXT DEFAULT 'Unknown'
                )
            """
            )
            
            # v1.0 Migration: Add new HR Intelligence columns to existing table
            try:
                self.con.execute("ALTER TABLE signals ADD COLUMN role_type TEXT DEFAULT 'Unknown'")
            except Exception:
                pass  # Column already exists
            
            try:
                self.con.execute("ALTER TABLE signals ADD COLUMN seniority_level TEXT DEFAULT 'Unknown'")
            except Exception:
                pass  # Column already exists

            # Regional Analysis Migration
            try:
                self.con.execute("ALTER TABLE signals ADD COLUMN region TEXT DEFAULT 'Unknown'")
            except Exception:
                pass  # Column already exists
            
            # v1.5 Ghost Job Detection
            try:
                self.con.execute("ALTER TABLE signals ADD COLUMN ghost_score INTEGER DEFAULT 0")
            except Exception:
                pass  # Column already exists

            # Create indexes for frequently queried columns
            # These dramatically improve performance for analytics queries
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_link ON signals(link)",
                "CREATE INDEX IF NOT EXISTS idx_source ON signals(source)",
                "CREATE INDEX IF NOT EXISTS idx_company ON signals(company)",
                "CREATE INDEX IF NOT EXISTS idx_tech_status ON signals(tech_status)",
                "CREATE INDEX IF NOT EXISTS idx_scraped_at ON signals(scraped_at)",
                "CREATE INDEX IF NOT EXISTS idx_last_seen_at ON signals(last_seen_at)",
                "CREATE INDEX IF NOT EXISTS idx_city ON signals(city)",
                "CREATE INDEX IF NOT EXISTS idx_region ON signals(region)",
                "CREATE INDEX IF NOT EXISTS idx_role_type ON signals(role_type)",
                "CREATE INDEX IF NOT EXISTS idx_seniority_level ON signals(seniority_level)"
            ]
            
            for idx_sql in indexes:
                try:
                    self.con.execute(idx_sql)
                except Exception:
                    # Index might already exist or read_only mode
                    pass
                    
        except Exception as e:
            # Silent fail if read_only doesn't allow table creation
            import logging
            logging.debug(f"Database initialization skipped (read-only mode): {e}")

    @property
    def df(self):
        """Lazy-loaded DataFrame with caching to avoid repeated DB queries."""
        # Cache is valid for 60 seconds
        if self._df_cache is None or (self._cache_timestamp and 
                                      (datetime.now() - self._cache_timestamp).seconds > 60):
            self._df_cache = self.con.execute("SELECT * FROM signals").df()
            self._cache_timestamp = datetime.now()
        return self._df_cache
    
    def load_as_df(self):
        """Force reload from database, bypassing cache."""
        self._df_cache = self.con.execute("SELECT * FROM signals").df()
        self._cache_timestamp = datetime.now()
        return self._df_cache

    def close(self):
        """Explicitly close the DuckDB connection."""
        if hasattr(self, 'con') and self.con:
            self.con.close()

    def is_known(self, url: str) -> bool:
        """O(1) lookup for existing signals and updates last_seen timestamp atomically."""
        # Use UPDATE...RETURNING pattern for atomic check-and-update
        # This prevents race conditions in concurrent scenarios
        now = datetime.now()
        
        # Try to update first - if it updates 0 rows, URL doesn't exist
        result = self.con.execute(
            "UPDATE signals SET last_seen_at = ? WHERE link = ? RETURNING 1",
            [now, url]
        ).fetchone()
        
        return result is not None

    def detect_ghost_jobs(self, signal: JobSignal) -> int:
        """
        Identify likely ghost jobs based on multiple indicators.
        Returns a score from 0 (legit) to 100 (ghost).
        """
        score = 0
        desc = (signal.description or "").lower()
        title = (signal.title or "").lower()
        
        # 1. Duplicate Listings by Company (check existing DB)
        try:
            dup_count = self.con.execute(
                "SELECT COUNT(*) FROM signals WHERE company = ? AND title = ?",
                [signal.company, signal.title]
            ).fetchone()[0]
            if dup_count > 3: score += 20
            if dup_count > 10: score += 30
        except Exception:
            pass

        # 2. Vague Description Indicators
        vague_phrases = [
            "ideal candidate", "rockstar", "ninja", "superhero",
            "we are always looking", "join our talent pool",
            "proaktivnĂ­ pĹ™Ă­stup", "tah na branku"
        ]
        if any(p in desc for p in vague_phrases):
            score += 15

        # 3. Unrealistic Requirements (Skill Stuffing)
        # Count technological keywords
        skills_count = len(re.findall(r'\b[a-z]{3,}\b', desc))
        if skills_count > 500: # Extremely long description
            score += 10
        
        # 4. Salary Range anomalies (if present)
        # Check happens in add_signal where parsed salary is available

        return min(score, 100)

    def add_signal(self, signal: JobSignal):
        """Adds a new signal with semantic enrichment and HR classification."""
        # Calculate semantic metrics
        tox = SemanticEngine.analyze_toxicity(signal.description)
        tech = SemanticEngine.analyze_tech_lag(signal.description)
        # Enhanced hash: pass link for better Remote job differentiation
        h = get_content_hash(signal.title, signal.company, signal.description, signal.location, signal.link)

        # v1.0 HR Intelligence: Role and Seniority classification
        role = JobClassifier.classify_role(signal.title, signal.description)
        seniority = JobClassifier.detect_seniority(signal.title, signal.description)

        # Robust Salary Parsing
        min_sal, max_sal, avg_sal = SalaryParser.parse(signal.salary, signal.source)

        # v1.5 Ghost Job Detection
        ghost_score = self.detect_ghost_jobs(signal)
        if min_sal and max_sal and min_sal > 0:
            # Check for > 100% spread (e.g. 40k - 120k)
            spread = (max_sal - min_sal) / min_sal
            if spread > 1.0:
                ghost_score += 25

        now = datetime.now()
        try:
            # v1.1 Regional Analysis: Default region to location for now
            # Proper normalization will be implemented in the next task
            region = signal.location if signal.location else "Unknown"
            
            self.con.execute(
                """
                INSERT OR IGNORE INTO signals 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    h,
                    signal.title,
                    signal.company,
                    signal.salary,
                    avg_sal,
                    signal.description,
                    signal.benefits,
                    signal.link,
                    signal.source,
                    signal.location,
                    region,
                    now,
                    tox,
                    tech,
                    now,
                    role,
                    seniority,
                    ghost_score,
                ],
            )
        except Exception as e:
            logger.error(f"DB Error: {e}")

    def get_summary(self):
        if self.df.empty:
            return "NO DATA"
        return self.con.execute(
            """
            SELECT source, count(*) as count, avg(avg_salary) as med_sal 
            FROM signals GROUP BY source
        """
        ).df()

    def cleanup_expired(self, threshold_minutes: int = 60):
        """Removes signals that haven't been seen in the current scrape session."""
        if not isinstance(threshold_minutes, int) or threshold_minutes < 0:
            raise ValueError("threshold_minutes must be a non-negative integer")
        
        before = self.con.execute("SELECT count(*) FROM signals").fetchone()[0]
        
        # Calculate the cutoff timestamp in Python to avoid SQL string formatting
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(minutes=threshold_minutes)
        
        self.con.execute(
            "DELETE FROM signals WHERE last_seen_at < ?",
            [cutoff]
        )
        
        after = self.con.execute("SELECT count(*) FROM signals").fetchone()[0]
        removed = before - after
        logger.info(f"Cleanup: Removed {removed} expired listings. {after} active signals remaining.")

    def reanalyze_all(self):
        """Re-runs semantic analysis and HR classification on all existing records."""
        logger.info("Re-analyzing all stored signals with v1.0 HR Intelligence...")
        rows = self.con.execute("SELECT hash, title, description, salary_raw, source FROM signals").fetchall()
        for h, title, desc, salary_str, source in rows:
            tox = SemanticEngine.analyze_toxicity(desc)
            tech = SemanticEngine.analyze_tech_lag(desc)
            role = JobClassifier.classify_role(title or "", desc or "")
            seniority = JobClassifier.detect_seniority(title or "", desc or "")
            
            # Re-parse salary to apply recent parser fixes (e.g. k-notation)
            min_sal, max_sal, avg_sal = SalaryParser.parse(salary_str, source)
            
            self.con.execute(
                "UPDATE signals SET toxicity_score = ?, tech_status = ?, role_type = ?, seniority_level = ?, avg_salary = ? WHERE hash = ?",
                [tox, tech, role, seniority, avg_sal, h]
            )
        # Invalidate cache after updates
        self.load_as_df()
        logger.info(f"v1.0 Migration complete: {len(rows)} signals updated with role/seniority/salary.")

    def vacuum_database(self):
        """Compact database to reclaim space from deleted records."""
        try:
            logger.info("Compacting database (VACUUM)...")
            self.con.execute("VACUUM")
            logger.info("Database compaction complete.")
        except Exception as e:
            logger.warning(f"Warning: VACUUM failed: {e}")

    def get_database_stats(self) -> dict:
        """Get comprehensive database statistics for monitoring."""
        try:
            total = self.con.execute("SELECT COUNT(*) FROM signals").fetchone()[0]

            # Get database file size
            db_size_bytes = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
            db_size_mb = db_size_bytes / (1024 * 1024)

            # Jobs by source
            by_source = {}
            source_data = self.con.execute(
                "SELECT source, COUNT(*) as cnt FROM signals GROUP BY source ORDER BY cnt DESC"
            ).fetchall()
            for source, count in source_data:
                by_source[source] = count

            # Timestamp info
            oldest = self.con.execute("SELECT MIN(scraped_at) FROM signals").fetchone()[0]
            newest = self.con.execute("SELECT MAX(scraped_at) FROM signals").fetchone()[0]

            return {
                'total_jobs': total,
                'db_size_mb': db_size_mb,
                'by_source': by_source,
                'oldest_job': str(oldest) if oldest else 'N/A',
                'newest_job': str(newest) if newest else 'N/A'
            }
        except Exception as e:
            return {
                'total_jobs': 0,
                'db_size_mb': 0,
                'by_source': {},
                'oldest_job': 'Error',
                'newest_job': f'Error: {e}'
            }


# Legacy class for App compatibility - now uses facade pattern to delegate to analysis modules
class MarketIntelligence:
    """
    Facade class providing backward-compatible API while delegating to focused analysis modules.
    
    Usage:
        intel = MarketIntelligence()
        intel.get_salary_by_role()  # Delegates to SalaryAnalysis
        intel.df  # Direct DataFrame access still works
    """
    
    def __init__(self):
        from analysis.salary_analysis import SalaryAnalysis
        from analysis.benefits_analysis import BenefitsAnalysis
        from analysis.location_analysis import LocationAnalysis
        from analysis.trends_analysis import TrendsAnalysis
        
        self.core = IntelligenceCore(read_only=True)
        self.df = self.core.df
        self._enrich_contract_type()
        
        # Compose analysis modules (delegation pattern)
        self._salary = SalaryAnalysis(self.df, TAXONOMY)
        self._benefits = BenefitsAnalysis(self.df, TAXONOMY)
        self._location = LocationAnalysis(self.df, TAXONOMY)
        self._trends = TrendsAnalysis(self.df, TAXONOMY)

    def _enrich_contract_type(self) -> None:
        """Enrich DataFrame with contract_type column."""
        if self.df.empty:
            self.df['contract_type'] = 'Unknown'
            return

        desc = self.df["description"].str.lower()
        ico_pat = "|".join(TAXONOMY['contract_keywords']['ico'])
        brig_pat = "|".join(TAXONOMY['contract_keywords']['brigada'])

        conds = [
            desc.str.contains(ico_pat, na=False),
            desc.str.contains(brig_pat, na=False)
        ]
        choices = ['IÄŚO', 'BrigĂˇda']
        self.df['contract_type'] = np.select(conds, choices, default='HPP')

    def load_ispv_benchmarks(self):
        """Loads official ISPV salary benchmarks from JSON"""
        try:
            path = os.path.join('data', 'ispv_salaries.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load ISPV benchmarks: {e}")
        return {}

    def analyze_skills(self, df):
        """Extracts top technical skills from description/title"""
        if 'title' not in df.columns and 'description' not in df.columns:
            return {}
            
        text_data = df['title'].fillna('') + ' ' + df.get('description', '').fillna('')
        all_text = ' '.join(text_data).lower()
        
        # Define skills with exclusions to remove soft skills
        tech_keywords = {
            'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue', 
            'node.js', 'sql', 'nosql', 'aws', 'azure', 'gcp', 'docker', 'kubernetes',
            'git', 'ci/cd', 'linux', 'agile', 'scrum', 'sap', 'salesforce', 'excel'
        }
        
        # Generic words to explicitly ignore if they appear in simple extraction
        ignore_words = {
            'communication', 'teamwork', 'english', 'czech', 'german', 'leadership', 
            'management', 'driving license', 'Ĺ™idiÄŤskĂ˝ prĹŻkaz', 'komunikace', 'tĂ˝movĂˇ prĂˇce'
        }
        
        found_skills = []
        # Simple word extraction (can be improved with regex/NLP)
        words = all_text.split()
        for word in words:
            clean_word = word.strip('.,()[]/').lower()
            if clean_word in tech_keywords and clean_word not in ignore_words:
                found_skills.append(clean_word)
                
        return dict(Counter(found_skills).most_common(15))

    def get_language_barrier(self):
        # Balanced NLP: requires a high density of English words without strict length penalties
        en_stops = set(TAXONOMY.get('nlp', {}).get('english_stops', []))

        def check_en(text):
            if not text:
                return False
            text_str = str(text).lower()
            words = set(re.findall(r'\b\w+\b', text_str))
            intersection = words.intersection(en_stops)
            
            # 3 unique English stop words is a very high signal for English-only JDs
            return len(intersection) >= 3

        en_count = self.df["description"].apply(check_en).sum()
        return {"English Friendly": en_count, "Czech Only": len(self.df) - en_count}

    def get_remote_truth(self):
        """Calculates jobs that are likely remote, with negative context handling."""
        remote_pattern = "|".join(TAXONOMY.get("remote_keywords", []))
        # Negative signals: "no remote", "office only", etc.
        rigid_pattern = r"no remote|not remote|office only|nenĂ­ remote|pouze v kancelĂˇĹ™i"
        
        desc = self.df["description"].fillna("").str.lower()
        is_remote_candidate = desc.str.contains(remote_pattern, case=False, na=False, regex=True)
        is_rigid = desc.str.contains(rigid_pattern, case=False, na=False, regex=True)
        
        true_remote_count = (is_remote_candidate & ~is_rigid).sum()
        return {"True Remote": int(true_remote_count)}

    def get_contract_split(self):
        """Get distribution of contract types."""
        if 'contract_type' not in self.df.columns:
            return {"HPP": 0, "IÄŚO": 0, "BrigĂˇda": 0}
            
        counts = self.df['contract_type'].value_counts()
        return {
            "HPP": int(counts.get('HPP', 0)),
            "IÄŚO": int(counts.get('IÄŚO', 0)),
            "BrigĂˇda": int(counts.get('BrigĂˇda', 0))
        }

    def get_tech_stack_lag(self):
        """Added missing method for Report compatibility."""
        return self.df['tech_status'].value_counts()

    def get_market_vibe(self):
        return self.df["tech_status"].value_counts()

    # --- v1.0 HR INTELLIGENCE METHODS ---
    
    def get_role_distribution(self) -> pd.DataFrame:
        """Get job distribution by role type."""
        return self.df['role_type'].value_counts().reset_index()
    
    def get_seniority_distribution(self) -> pd.DataFrame:
        """Get job distribution by seniority level."""
        return self.df['seniority_level'].value_counts().reset_index()
    
    def get_salary_by_role(self) -> pd.DataFrame:
        """Get median salary breakdown by role type. Delegates to SalaryAnalysis."""
        return self._salary.get_salary_by_role()
    
    def get_salary_by_seniority(self) -> pd.DataFrame:
        """Get median salary breakdown by seniority level. Delegates to SalaryAnalysis."""
        return self._salary.get_salary_by_seniority()

    def get_salary_by_contract_type(self) -> dict:
        """Get median salary for HPP vs BrigĂˇda. Delegates to SalaryAnalysis."""
        return self._salary.get_salary_by_contract_type()

    def get_seniority_role_matrix(self) -> pd.DataFrame:
        """Cross-analysis: Median salary by Seniority + Role. Delegates to SalaryAnalysis."""
        return self._salary.get_seniority_role_matrix()
    
    def get_skill_premiums(self) -> pd.DataFrame:
        """Calculate salary premium for top skills. Delegates to SalaryAnalysis."""
        return self._salary.get_skill_premiums()

    # --- v1.1 BENEFITS INTELLIGENCE ---

    def get_benefits_analysis(self) -> pd.DataFrame:
        """Analyze which benefits are most commonly offered. Delegates to BenefitsAnalysis."""
        return self._benefits.get_benefits_analysis()

    def get_benefits_by_role(self) -> pd.DataFrame:
        """Show which roles get the best benefits. Delegates to BenefitsAnalysis."""
        return self._benefits.get_benefits_by_role()

    # --- v1.1 LOCATION INTELLIGENCE ---

    def get_salary_by_city(self) -> pd.DataFrame:
        """Get median salary breakdown by city/location. Delegates to SalaryAnalysis."""
        return self._salary.get_salary_by_city()

    def get_location_distribution(self) -> pd.DataFrame:
        """Get job distribution by location. Delegates to LocationAnalysis."""
        return self._location.get_location_distribution()

    # --- v1.1 WORK MODEL INTELLIGENCE ---

    def get_work_model_distribution(self) -> dict:
        """Classify jobs by work model. Delegates to LocationAnalysis."""
        result = self._location.get_work_model_distribution()
        # Convert DataFrame to dict format for backward compatibility
        if isinstance(result, pd.DataFrame):
            return dict(zip(result['Work Model'], result['Count']))
        return result

    def get_work_model_by_role(self) -> pd.DataFrame:
        """Show work model distribution for top roles."""
        work_model_kw = TAXONOMY.get('work_model_keywords', {})

        remote_pattern = '|'.join(work_model_kw.get('remote', []))
        hybrid_pattern = '|'.join(work_model_kw.get('hybrid', []))

        desc = self.df['description'].fillna('').str.lower()

        # Classify each job
        def classify_work_model(desc_text):
            if not isinstance(desc_text, str):
                return 'Office'
            desc_lower = desc_text.lower()
            if re.search(remote_pattern, desc_lower):
                return 'Remote'
            elif re.search(hybrid_pattern, desc_lower):
                return 'Hybrid'
            return 'Office'

        self.df['work_model_temp'] = self.df['description'].apply(classify_work_model)

        # Get top 5 roles
        top_roles = self.df['role_type'].value_counts().head(5).index
        filtered = self.df[self.df['role_type'].isin(top_roles)]

        # Cross-tabulate
        result = pd.crosstab(filtered['role_type'], filtered['work_model_temp'], normalize='index') * 100
        result = result.round(1).reset_index()

        # Clean up temp column
        self.df.drop('work_model_temp', axis=1, inplace=True, errors='ignore')

        return result

    def get_remote_salary_premium(self) -> dict:
        """Calculate salary premium for remote vs office jobs. Delegates to SalaryAnalysis."""
        return self._salary.get_remote_salary_premium()

    # --- v1.2 TEMPORAL & EMERGING TRENDS ---

    def get_salary_trend_weekly(self) -> pd.DataFrame:
        """Get weekly median salary trends. Delegates to SalaryAnalysis."""
        return self._salary.get_salary_trend_weekly()

    def get_emerging_tech_signals(self) -> pd.DataFrame:
        """
        Detect hot/emerging technologies based on mention frequency using accurate patterns.
        """
        # Use skill_patterns from taxonomy for accurate detection
        skill_patterns = TAXONOMY.get('skill_patterns', {})

        results = []
        for tech_name, pattern in skill_patterns.items():
            try:
                mask = self.df['description'].fillna('').str.lower().str.contains(pattern, regex=True, case=False, na=False)
                count = mask.sum()
                percentage = (count / len(self.df)) * 100

                if count >= 10:  # Minimum threshold for significance (lowered from 50)
                    results.append({
                        'Technology': tech_name,
                        'Jobs': int(count),
                        'Market Share': f"{percentage:.1f}%",
                        'Share_Raw': percentage
                    })
            except Exception as e:
                # Fallback to simple matching if regex fails
                import logging
                logging.debug(f"Regex failed for {tech_name}: {e}")
                mask = self.df['description'].fillna('').str.lower().str.contains(tech_name.lower(), regex=False)
                count = mask.sum()
                percentage = (count / len(self.df)) * 100
                if count >= 10:
                    results.append({
                        'Technology': tech_name,
                        'Jobs': int(count),
                        'Market Share': f"{percentage:.1f}%",
                        'Share_Raw': percentage
                    })

        if not results:
            return pd.DataFrame(columns=['Technology', 'Jobs', 'Market Share'])

        return pd.DataFrame(results).sort_values('Share_Raw', ascending=False).drop('Share_Raw', axis=1).head(15)

    def get_new_market_entrants(self) -> pd.DataFrame:
        """
        Identify companies that recently entered the job market (5-15 job postings).
        Could indicate growing startups or expansion.
        """
        company_counts = self.df['company'].value_counts()

        # Filter companies with 5-15 postings (active but not yet saturated)
        emerging_companies = company_counts[(company_counts >= 5) & (company_counts <= 15)]

        if emerging_companies.empty:
            return pd.DataFrame(columns=['Company', 'Active Jobs'])

        result = pd.DataFrame({
            'Company': emerging_companies.index,
            'Active Jobs': emerging_companies.values
        }).sort_values('Active Jobs', ascending=False).head(10)

        # Clean company names
        result['Company'] = result['Company'].apply(lambda x: ' '.join(x.lstrip('â€˘\u2022\u2023\u25E6\u25AA\u25AB').strip().split()))

        return result

    def get_trending_benefits(self) -> pd.DataFrame:
        """
        Show fastest-growing benefits (based on frequency).
        For single-day data, this shows current hot benefits.
        """
        benefits_cats = TAXONOMY.get('benefits_keywords', {})

        results = []
        for benefit_name, keywords in benefits_cats.items():
            pattern = '|'.join([re.escape(kw) for kw in keywords])
            mask = self.df['description'].fillna('').str.lower().str.contains(pattern, regex=True, case=False)
            count = mask.sum()
            percentage = (count / len(self.df)) * 100

            if count >= 100:  # Minimum threshold
                display_name = BENEFIT_DISPLAY_NAMES.get(benefit_name, benefit_name.title())
                results.append({
                    'Benefit': display_name,
                    'Adoption': f"{percentage:.1f}%",
                    'Jobs': int(count),
                    'Adoption_Raw': percentage
                })

        if not results:
            return pd.DataFrame(columns=['Benefit', 'Adoption', 'Jobs'])

        return pd.DataFrame(results).sort_values('Adoption_Raw', ascending=False).drop('Adoption_Raw', axis=1).head(6)

    def get_data_freshness_report(self) -> dict:
        """
        Report on data temporal coverage for trend analysis readiness.
        """
        import pandas as pd
        
        if self.df.empty:
            return {
                'unique_dates': 0,
                'date_range_days': 0,
                'earliest_date': 'N/A',
                'latest_date': 'N/A',
                'trend_analysis_ready': False
            }

        df_copy = self.df.copy()
        df_copy['scraped_date'] = pd.to_datetime(df_copy['scraped_at']).dt.date

        unique_dates = df_copy['scraped_date'].nunique()
        date_range = (df_copy['scraped_at'].max() - df_copy['scraped_at'].min()).days

        return {
            'unique_dates': int(unique_dates),
            'date_range_days': int(date_range) if pd.notna(date_range) else 0,
            'earliest_date': str(df_copy['scraped_at'].min()),
            'latest_date': str(df_copy['scraped_at'].max()),
            'trend_analysis_ready': unique_dates >= 7
        }

    # --- v1.3 ECONOMIC REALITY & TALENT DYNAMICS ---

    def get_ico_hpp_arbitrage(self) -> dict:
        """
        Calculate the IÄŚO (contractor) vs HPP (employee) salary premium.
        Reveals tax optimization pressure.
        """
        valid_sal = self.df[self.df['avg_salary'] > 0]

        # Classify by contract type
        ico_pattern = '|'.join(TAXONOMY['contract_keywords']['ico'])
        brigada_pattern = '|'.join(TAXONOMY['contract_keywords']['brigada'])

        desc = valid_sal['description'].fillna('').str.lower()

        is_ico = desc.str.contains(ico_pattern, case=False, na=False, regex=True)
        is_brigada = desc.str.contains(brigada_pattern, case=False, na=False, regex=True)

        # HPP is everything that's NOT IÄŚO or BrigĂˇda
        is_hpp = ~(is_ico | is_brigada)

        ico_median = valid_sal[is_ico]['avg_salary'].median()
        hpp_median = valid_sal[is_hpp]['avg_salary'].median()

        ico_count = is_ico.sum()
        hpp_count = is_hpp.sum()

        if pd.notna(ico_median) and pd.notna(hpp_median) and hpp_median > 0 and ico_count >= 20 and hpp_count >= 20:
            premium_pct = int(((ico_median / hpp_median) - 1) * 100)
            return {
                'ico_median': int(ico_median),
                'hpp_median': int(hpp_median),
                'premium': f"+{premium_pct}%" if premium_pct >= 0 else f"{premium_pct}%",
                'premium_raw': premium_pct,
                'ico_count': int(ico_count),
                'hpp_count': int(hpp_count),
                'available': True
            }

        return {'ico_median': 0, 'hpp_median': 0, 'premium': 'N/A', 'premium_raw': 0, 'ico_count': int(ico_count), 'hpp_count': int(hpp_count), 'available': False}

    def get_language_barrier_cost(self) -> dict:
        """
        Salary difference between Czech-only vs English-friendly roles.
        Measures market globalization.
        """
        valid_sal = self.df[self.df['avg_salary'] > 0]

        # English keywords
        en_pattern = r'\benglish\b|\ben\b language|\binternational\b|\bglobal\b'
        desc = valid_sal['description'].fillna('').str.lower()

        is_english = desc.str.contains(en_pattern, case=False, na=False, regex=True)

        en_median = valid_sal[is_english]['avg_salary'].median()
        cz_median = valid_sal[~is_english]['avg_salary'].median()

        en_count = is_english.sum()
        cz_count = (~is_english).sum()

        if pd.notna(en_median) and pd.notna(cz_median) and cz_median > 0 and en_count >= 50:
            premium_pct = int(((en_median / cz_median) - 1) * 100)
            return {
                'english_median': int(en_median),
                'czech_median': int(cz_median),
                'premium': f"+{premium_pct}%" if premium_pct >= 0 else f"{premium_pct}%",
                'premium_raw': premium_pct,
                'english_count': int(en_count),
                'czech_count': int(cz_count),
                'available': True
            }

        return {'english_median': 0, 'czech_median': 0, 'premium': 'N/A', 'premium_raw': 0, 'english_count': int(en_count), 'czech_count': int(cz_count), 'available': False}

    def get_talent_pipeline_health(self) -> dict:
        """
        Junior:Senior ratio. Healthy = 1:3 to 1:4.
        1:10+ indicates "missing generation" problem.
        """
        junior_count = len(self.df[self.df['seniority_level'] == 'Junior'])
        senior_count = len(self.df[self.df['seniority_level'] == 'Senior'])
        mid_count = len(self.df[self.df['seniority_level'] == 'Mid'])
        lead_count = len(self.df[self.df['seniority_level'] == 'Lead'])
        exec_count = len(self.df[self.df['seniority_level'] == 'Executive'])

        if junior_count > 0 and senior_count > 0:
            ratio = senior_count / junior_count

            # Health assessment
            if ratio <= 4:
                health = "Healthy"
                health_color = "green"
            elif ratio <= 7:
                health = "Caution"
                health_color = "orange"
            else:
                health = "Missing Generation"
                health_color = "red"

            return {
                'junior': junior_count,
                'mid': mid_count,
                'senior': senior_count,
                'lead': lead_count,
                'executive': exec_count,
                'ratio': f"1:{ratio:.1f}",
                'ratio_raw': ratio,
                'health': health,
                'health_color': health_color,
                'available': True
            }

        return {'junior': junior_count, 'mid': mid_count, 'senior': senior_count, 'lead': lead_count, 'executive': exec_count, 'ratio': 'N/A', 'ratio_raw': 0, 'health': 'Unknown', 'health_color': 'gray', 'available': False}

    def get_remote_flexibility_analysis(self) -> pd.DataFrame:
        """
        Semantic analysis of "Hybrid" - rigid vs flexible.
        Detects phrases like "2 days fixed", "mandatory office", "flexible arrangement".
        """
        work_model_kw = TAXONOMY.get('work_model_keywords', {})
        hybrid_pattern = '|'.join(work_model_kw.get('hybrid', []))

        desc = self.df['description'].fillna('').str.lower()
        is_hybrid = desc.str.contains(hybrid_pattern, case=False, na=False, regex=True)

        hybrid_jobs = self.df[is_hybrid].copy()

        if len(hybrid_jobs) == 0:
            return pd.DataFrame(columns=['Flexibility', 'Count', 'Percentage'])

        # Detect rigidity signals (non-capturing groups to avoid pandas warning)
        rigid_signals = r'2 days?\s+(?:office|kancelĂˇĹ™)|fixed days?|povinnĂˇ pĹ™Ă­tomnost|mandatory office|3\s*days?\s*week'
        flexible_signals = r'flexible|volnÄ›|kdykoliv|come if you want|podle potĹ™eby|flexibilnĂ­'

        hybrid_jobs['is_rigid'] = hybrid_jobs['description'].fillna('').str.lower().str.contains(rigid_signals, regex=True, case=False, na=False)
        hybrid_jobs['is_flexible'] = hybrid_jobs['description'].fillna('').str.lower().str.contains(flexible_signals, regex=True, case=False, na=False)

        rigid_count = hybrid_jobs['is_rigid'].sum()
        flexible_count = hybrid_jobs['is_flexible'].sum()
        unclear_count = len(hybrid_jobs) - rigid_count - flexible_count

        total = len(hybrid_jobs)

        results = [
            {'Flexibility': 'Rigid (Fixed Days)', 'Count': int(rigid_count), 'Percentage': f"{(rigid_count/total)*100:.1f}%"},
            {'Flexibility': 'Flexible', 'Count': int(flexible_count), 'Percentage': f"{(flexible_count/total)*100:.1f}%"},
            {'Flexibility': 'Unclear', 'Count': int(unclear_count), 'Percentage': f"{(unclear_count/total)*100:.1f}%"}
        ]

        return pd.DataFrame(results)

    def get_legacy_rot_by_role(self) -> pd.DataFrame:
        """
        Legacy tech % by role. Measures "tech debt" of each profession.
        """
        top_roles = self.df['role_type'].value_counts().head(8).index
        filtered = self.df[self.df['role_type'].isin(top_roles)]

        results = []
        for role in top_roles:
            role_df = filtered[filtered['role_type'] == role]

            legacy_count = len(role_df[role_df['tech_status'] == 'Dinosaur'])
            modern_count = len(role_df[role_df['tech_status'] == 'Modern'])
            total = len(role_df)

            legacy_pct = (legacy_count / total) * 100 if total > 0 else 0
            modern_pct = (modern_count / total) * 100 if total > 0 else 0

            results.append({
                'Role': role,
                'Legacy %': f"{legacy_pct:.1f}%",
                'Modern %': f"{modern_pct:.1f}%",
                'Total Jobs': total,
                'Legacy_Raw': legacy_pct
            })

        if not results:
            return pd.DataFrame(columns=['Role', 'Legacy %', 'Modern %', 'Total Jobs'])

        return pd.DataFrame(results).sort_values('Legacy_Raw', ascending=False).drop('Legacy_Raw', axis=1)

    def get_ai_washing_nontech(self) -> dict:
        """
        Detect AI/ChatGPT/ML mentions in non-tech roles (HR, Marketing, Admin, Sales).
        Measures "AI hype" penetration.
        """
        # Define non-tech roles
        nontech_roles = ['HR', 'Sales', 'Marketing', 'Support', 'Management', 'Admin', 'Operations']

        nontech_df = self.df[self.df['role_type'].isin(nontech_roles)]

        if len(nontech_df) == 0:
            return {'total_nontech': 0, 'ai_mentions': 0, 'percentage': 'N/A', 'available': False}

        # AI keywords
        ai_pattern = r'\bai\b|\bchatgpt\b|\bgpt\b|\bmachine learning\b|\bml\b|\bgenerat|\bart.*intelligence'

        desc = nontech_df['description'].fillna('').str.lower()
        has_ai = desc.str.contains(ai_pattern, case=False, na=False, regex=True)

        ai_count = has_ai.sum()
        total = len(nontech_df)
        percentage = (ai_count / total) * 100

        return {
            'total_nontech': int(total),
            'ai_mentions': int(ai_count),
            'percentage': f"{percentage:.1f}%",
            'percentage_raw': percentage,
            'available': True
        }

    def get_ghost_jobs(self) -> pd.DataFrame:
        """
        Detect jobs that appear frequently or stay active unusually long.
        With current single-day data: identifies high-volume repeat posters.
        """
        # For now, detect companies posting the same role title multiple times
        title_company_counts = self.df.groupby(['company', 'title']).size().reset_index(name='Count')

        # Flag as potential ghost jobs if same title posted 3+ times by same company
        ghosts = title_company_counts[title_company_counts['Count'] >= 3].sort_values('Count', ascending=False)

        if len(ghosts) == 0:
            return pd.DataFrame(columns=['Company', 'Title', 'Repost Count'])

        ghosts = ghosts.head(15)
        ghosts.columns = ['Company', 'Title', 'Repost Count']

        # Clean company names
        ghosts['Company'] = ghosts['Company'].apply(lambda x: ' '.join(x.lstrip('â€˘\u2022\u2023\u25E6\u25AA\u25AB').strip().split()))

        return ghosts



