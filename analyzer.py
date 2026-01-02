import pandas as pd
import re
import os
import hashlib
import unicodedata
import duckdb
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

# --- ARCHITECTURAL CONSTANTS ---
DB_PATH = "data/intelligence.db"


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


def normalize_text(text):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    # Remove dots used as thousand separators, standardizing digits
    text = re.sub(r"(\d)\.(\d{3})", r"\1\2", text)
    return text.strip()


def get_content_hash(title, company, description):
    raw = f"{title}{company}{str(description)[:500]}".lower()
    clean = re.sub(r"\W+", "", raw)
    return hashlib.md5(clean.encode()).hexdigest()


class SemanticEngine:
    """Simulates AI logic using high-fidelity keyword weighting (NER Lite)."""

    @staticmethod
    def analyze_toxicity(description):
        """Detects toxic red flags in JDs."""
        flags = [
            "asap",
            "stress",
            "pressure",
            "flexible hours (meaning always)",
            "rockstar",
            "ninja",
            "family (red flag)",
        ]
        d = description.lower()
        score = sum(30 for f in flags if f in d)
        return min(score, 100)

    @staticmethod
    def analyze_tech_lag(description):
        """Calculates technological obsolescence score."""
        legacy = [
            "jquery", "angularjs", "tensorflow", "svn", "php 5", "java 8", 
            "struts", "wordpress", "prestashop", "silverlight", "delphi",
            "vb6", "cobol", "waterfall"
        ]
        modern = [
            "pytorch", "fastapi", "rust", "go", "next.js", "tailwindcss", 
            "generative", "llm", "kubernetes", "docker", "typescript", 
            "react", "aws", "azure", "serverless", "agile", "scrum"
        ]
        d = description.lower()
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
        self.df = self.load_as_df()

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
        except:
            pass  # Silent fail if read_only doesn't allow creation

    def load_as_df(self):
        return self.con.execute("SELECT * FROM signals").df()

    def is_known(self, url):
        """O(1) lookup for existing signals and updates last_seen timestamp."""
        res = self.con.execute(
            "SELECT count(*) FROM signals WHERE link = ?", [url]
        ).fetchone()
        if res[0] > 0:
            self.con.execute("UPDATE signals SET last_seen_at = ? WHERE link = ?", [datetime.now(), url])
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

    def _parse_salary(self, s):
        if not s or not isinstance(s, str):
            return None, None, None
        s = s.lower().replace(" ", "").replace("\xa0", "").replace(".", "")
        nums = [int(n) for n in re.findall(r"(\d+)", s) if int(n) > 1000]
        
        # Handle EUR
        if "eur" in s:
            nums = [n * 25 for n in nums]
        
        if not nums:
            return None, None, None
        v = sum(nums) / len(nums)
        return v, v, v

    def get_summary(self):
        if self.df.empty:
            return "NO DATA"
        return self.con.execute(
            """
            SELECT source, count(*) as count, avg(avg_salary) as med_sal 
            FROM signals GROUP BY source
        """
        ).df()

    def cleanup_expired(self, threshold_minutes=60):
        """Removes signals that haven't been seen in the current scrape session."""
        before = self.con.execute("SELECT count(*) FROM signals").fetchone()[0]
        
        # Fixed DuckDB syntax for interval subtraction with parameters
        self.con.execute(
            f"DELETE FROM signals WHERE last_seen_at < (CURRENT_TIMESTAMP - INTERVAL '{threshold_minutes}' MINUTE)"
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
        self.df = self.load_as_df()
        print(f"Migration complete: {len(rows)} signals updated.")


# Legacy class for App compatibility
class MarketIntelligence:
    def __init__(self):
        self.core = IntelligenceCore(read_only=True)
        self.df = self.core.df

    def get_language_barrier(self):
        # Improved NLP: common English stop words and punctuation removal
        en_stops = {"the", "and", "with", "team", "from", "for", "that", "this", "our", "will"}

        def check_en(text):
            if not text:
                return False
            # Normalize: lowercase and remove non-alphanumeric for better matching
            words = set(re.findall(r'\b\w+\b', str(text).lower()))
            # Intersection of 3+ words is a strong signal for English JD
            return len(words.intersection(en_stops)) >= 3

        en_count = self.df["description"].apply(check_en).sum()
        return {"English Friendly": en_count, "Czech Only": len(self.df) - en_count}

    def get_remote_truth(self):
        # Added Czech keywords for Remote work detection
        remote_pattern = r"remote|home office|prace z domova|praca z domu|vzdalene|full-remote|hybrid"
        is_remote = (
            self.df["description"]
            .str.contains(remote_pattern, case=False, na=False, regex=True)
            .sum()
        )
        return {"True Remote": is_remote}

    def get_contract_split(self):
        # Broaden ICO detection
        ico_pattern = r"ico|faktur|zivnost|osvc"
        ico = (
            self.df["description"]
            .str.contains(ico_pattern, case=False, na=False, regex=True)
            .sum()
        )
        return {"HPP": len(self.df) - ico, "ICO": ico}

    def get_tech_stack_lag(self):
        """Added missing method for Report compatibility."""
        return self.df['tech_status'].value_counts()

    def get_market_vibe(self):
        return self.df["tech_status"].value_counts()