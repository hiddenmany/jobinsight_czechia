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
            "jquery",
            "angularjs",
            "tensorflow",
            "svn",
            "php 5",
            "java 8",
            "struts",
        ]
        modern = [
            "pytorch",
            "fastapi",
            "rust",
            "go",
            "next.js",
            "tailwindcss",
            "generative",
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
                    tech_status TEXT
                )
            """
            )
        except:
            pass  # Silent fail if read_only doesn't allow creation

    def load_as_df(self):
        return self.con.execute("SELECT * FROM signals").df()

    def is_known(self, url):
        """O(1) lookup for existing signals."""
        res = self.con.execute(
            "SELECT count(*) FROM signals WHERE link = ?", [url]
        ).fetchone()
        return res[0] > 0

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

        try:
            self.con.execute(
                """
                INSERT OR IGNORE INTO signals 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    datetime.now(),
                    tox,
                    tech,
                ],
            )
        except Exception as e:
            print(f"DB Error: {e}")

    def _parse_salary(self, s):
        if not s or not isinstance(s, str):
            return None, None, None
        s = s.lower().replace(" ", "").replace("\xa0", "")
        nums = [int(n) for n in re.findall(r"(\d+)", s) if int(n) > 1000]
        if not nums:
            return None, None, None
        v = sum(nums) / len(nums)  # Simplistic average for the DB store
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


# Legacy class for App compatibility
class MarketIntelligence:
    def __init__(self):
        self.core = IntelligenceCore(read_only=True)
        self.df = self.core.df

    def get_language_barrier(self):
        # Heuristic implementation for the Swiss UI
        en_stops = {"the", "and", "with", "team"}

        def check_en(text):
            if not text:
                return False
            words = set(str(text).lower().split())
            return len(words.intersection(en_stops)) > 2

        en_count = self.df["description"].apply(check_en).sum()
        return {"English Friendly": en_count, "Czech Only": len(self.df) - en_count}

    def get_remote_truth(self):
        is_remote = (
            self.df["description"]
            .str.contains("remote|home office", case=False, na=False)
            .sum()
        )
        return {"True Remote": is_remote}  # Simplified

    def get_contract_split(self):
        ico = (
            self.df["description"]
            .str.contains("ico|faktur", case=False, na=False)
            .sum()
        )
        return {"HPP": len(self.df) - ico, "ICO": ico}

    def get_tech_stack_lag(self):
        """Added missing method for Report compatibility."""
        return self.df['tech_status'].value_counts()

    def get_market_vibe(self):
        return self.df["tech_status"].value_counts()