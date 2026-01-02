import pandas as pd
import re
import os
import hashlib
import unicodedata
import duckdb
import yaml
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

# --- ARCHITECTURAL CONSTANTS ---
DB_PATH = "data/intelligence.db"
TAXONOMY_PATH = os.path.join(os.path.dirname(__file__), "config", "taxonomy.yaml")

def load_taxonomy():
    with open(TAXONOMY_PATH, 'r') as f:
        return yaml.safe_load(f)

TAXONOMY = load_taxonomy()

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
    location: str = "CZ"


def normalize_text(text: str) -> str:
    """Normalize text by removing Unicode variations and thousand separators."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    # Remove dots used as thousand separators, standardizing digits
    text = re.sub(r"(\d)\.(\d{3})", r"\1\2", text)
    return text.strip()


def get_content_hash(title: str, company: str, description: str) -> str:
    """Generate a unique hash for content deduplication using SHA256."""
    raw = f"{title}{company}{str(description)[:500]}".lower()
    clean = re.sub(r"\W+", "", raw)
    return hashlib.sha256(clean.encode()).hexdigest()


class SemanticEngine:
    """Simulates AI logic using high-fidelity keyword weighting (NER Lite)."""

    @staticmethod
    def is_tech_relevant(title: str, description: str) -> bool:
        """Filters out non-tech signals to keep the report focused."""
        # Using a subset of modern/legacy for relevance check
        tech_keywords = set(TAXONOMY['tech_stack']['modern'] + TAXONOMY['tech_stack']['legacy'])
        text = f"{title} {description}".lower()
        return any(k in text for k in tech_keywords)

    @staticmethod
    def analyze_toxicity(description: str) -> int:
        """Detects toxic red flags in JDs. Returns score 0-100."""
        flags = TAXONOMY.get('toxicity', {}).get('red_flags', [])
        d = description.lower() if description else ""
        score = sum(30 for f in flags if f in d)
        return min(score, 100)

    @staticmethod
    def analyze_tech_lag(description: str) -> str:
        """Calculates technological obsolescence score. Returns 'Modern', 'Stable', or 'Dinosaur'."""
        legacy = TAXONOMY['tech_stack']['legacy']
        modern = TAXONOMY['tech_stack']['modern']
        d = description.lower() if description else ""
        legacy_hit = sum(1 for x in legacy if x in d)
        modern_hit = sum(1 for x in modern if x in d)

        if legacy_hit > modern_hit:
            return "Dinosaur"
        if modern_hit > legacy_hit:
            return "Modern"
        return "Stable"


class IntelligenceCore:
    """The central stateful data brain using DuckDB."""

    def __init__(self, read_only=False):
        os.makedirs("data", exist_ok=True)
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
                    scraped_at TIMESTAMP,
                    toxicity_score INTEGER,
                    tech_status TEXT,
                    last_seen_at TIMESTAMP
                )
            """
            )
            
            # Create indexes for frequently queried columns
            # These dramatically improve performance for analytics queries
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_link ON signals(link)",
                "CREATE INDEX IF NOT EXISTS idx_source ON signals(source)",
                "CREATE INDEX IF NOT EXISTS idx_company ON signals(company)",
                "CREATE INDEX IF NOT EXISTS idx_tech_status ON signals(tech_status)",
                "CREATE INDEX IF NOT EXISTS idx_scraped_at ON signals(scraped_at)",
                "CREATE INDEX IF NOT EXISTS idx_last_seen_at ON signals(last_seen_at)",
                "CREATE INDEX IF NOT EXISTS idx_city ON signals(city)"
            ]
            
            for idx_sql in indexes:
                try:
                    self.con.execute(idx_sql)
                except Exception as e:
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

    def is_known(self, url: str) -> bool:
        """O(1) lookup for existing signals and updates last_seen timestamp atomically."""
        # First check if URL exists, then update in single transaction-like flow
        # DuckDB doesn't support RETURNING clause for UPDATE, so we do a conditional update
        res = self.con.execute(
            "SELECT 1 FROM signals WHERE link = ? LIMIT 1", [url]
        ).fetchone()
        
        if res is not None:
            # URL exists, update the timestamp
            self.con.execute(
                "UPDATE signals SET last_seen_at = ? WHERE link = ?", 
                [datetime.now(), url]
            )
            return True
        return False

    def add_signal(self, signal: JobSignal):
        """Adds a new signal with semantic enrichment."""
        # Calculate semantic metrics
        tox = SemanticEngine.analyze_toxicity(signal.description)
        tech = SemanticEngine.analyze_tech_lag(signal.description)
        h = get_content_hash(
            signal.title, signal.company, signal.description
        )

        # Robust Salary Parsing
        _, _, avg_sal = self._parse_salary(signal.salary)

        now = datetime.now()
        try:
            self.con.execute(
                """
                INSERT OR IGNORE INTO signals 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    now,
                    tox,
                    tech,
                    now,
                ],
            )
        except Exception as e:
            print(f"DB Error: {e}")

    def _parse_salary(self, s: str) -> tuple:
        """
        Parse salary string and return (min_salary, max_salary, avg_salary).
        
        Returns:
            tuple: (min, max, avg) salary values, or (None, None, None) if parsing fails
        """
        if not s or not isinstance(s, str):
            return None, None, None
        s = s.lower().replace(" ", "").replace("\xa0", "").replace(".", "")
        nums = [int(n) for n in re.findall(r"(\d+)", s) if int(n) > 1000]
        
        # Handle EUR conversion to CZK (approximate rate)
        if "eur" in s:
            nums = [n * 25 for n in nums]
        
        if not nums:
            return None, None, None
        
        min_sal = min(nums)
        max_sal = max(nums)
        avg_sal = sum(nums) / len(nums)
        return min_sal, max_sal, avg_sal

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
        print(f"Cleanup: Removed {removed} expired listings. {after} active signals remaining.")

    def reanalyze_all(self):
        """Re-runs semantic analysis on all existing records to update metrics."""
        print("Re-analyzing all stored signals with updated NLP logic...")
        rows = self.con.execute("SELECT hash, description FROM signals").fetchall()
        for h, desc in rows:
            tox = SemanticEngine.analyze_toxicity(desc)
            tech = SemanticEngine.analyze_tech_lag(desc)
            self.con.execute(
                "UPDATE signals SET toxicity_score = ?, tech_status = ? WHERE hash = ?",
                [tox, tech, h]
            )
        # Invalidate cache after updates
        self.load_as_df()
        print(f"Migration complete: {len(rows)} signals updated.")


# Legacy class for App compatibility
class MarketIntelligence:
    def __init__(self):
        self.core = IntelligenceCore(read_only=True)
        self.df = self.core.df

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
        # Using remote keywords from taxonomy
        remote_pattern = "|".join(TAXONOMY.get('remote_keywords', []))
        is_remote = (
            self.df["description"]
            .str.contains(remote_pattern, case=False, na=False, regex=True)
            .sum()
        )
        return {"True Remote": is_remote}

    def get_contract_split(self):
        # Multi-category contract detection using taxonomy
        desc = self.df["description"].str.lower()
        
        ico_pat = "|".join(TAXONOMY['contract_keywords']['ico'])
        brig_pat = "|".join(TAXONOMY['contract_keywords']['brigada'])
        
        # Priority: ICO > Brigada > HPP (Standard)
        # This ensures categories are mutually exclusive for the Pie Chart
        is_ico = desc.str.contains(ico_pat, na=False)
        is_brigada = desc.str.contains(brig_pat, na=False) & ~is_ico
        
        ico_count = is_ico.sum()
        brig_count = is_brigada.sum()
        hpp_count = len(self.df) - ico_count - brig_count
        
        return {"HPP": max(0, hpp_count), "IČO": ico_count, "Brigáda": brig_count}

    def get_tech_stack_lag(self):
        """Added missing method for Report compatibility."""
        return self.df['tech_status'].value_counts()

    def get_market_vibe(self):
        return self.df["tech_status"].value_counts()