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

# Compiled regex patterns for performance (Fix 4.3)
SALARY_DIGITS_PATTERN = re.compile(r"(\d+)")
THOUSAND_SEP_PATTERN = re.compile(r"(\d)\.(\d{3})")

# --- v1.0 HR INTELLIGENCE: Role Classification ---
ROLE_TAXONOMY = {
    'Developer': ['developer', 'programátor', 'engineer', 'vývojář', 'frontend', 'backend', 
                  'fullstack', 'full-stack', 'software', 'web developer', 'mobile developer', 
                  'devops', 'sre', 'platform engineer', 'embedded'],
    'Analyst': ['analyst', 'analytik', 'data analyst', 'business analyst', 'bi analyst', 
                'data scientist', 'data engineer', 'reporting'],
    'Designer': ['designer', 'ux', 'ui', 'grafik', 'product designer', 'visual designer', 
                 'creative', 'art director'],
    'QA': ['tester', 'qa', 'quality', 'test engineer', 'automation', 'sdet'],
    'PM': ['project manager', 'product manager', 'scrum master', 'agile coach', 
           'projektový manažer', 'product owner', 'delivery manager'],
    'Sales': ['sales', 'obchodní', 'account', 'business development', 'key account', 
              'obchodník', 'rep', 'account executive'],
    'HR': ['hr', 'recruiter', 'talent', 'people', 'personalist', 'nábor', 'recruitment'],
    'Marketing': ['marketing', 'seo', 'content', 'social media', 'brand', 'growth', 
                  'ppc', 'performance marketing', 'copywriter'],
    'Support': ['support', 'customer', 'helpdesk', 'podpora', 'zákaznick', 'service desk'],
    'Operations': ['operations', 'admin', 'assistant', 'office', 'back office', 'koordinátor'],
    'Finance': ['accountant', 'účetní', 'finance', 'controller', 'controlling', 'fakturace'],
    'Management': ['head of', 'director', 'cto', 'ceo', 'vp', 'lead', 'manager', 'vedoucí', 
                   'ředitel', 'team lead', 'tech lead']
}

# --- v1.0 HR INTELLIGENCE: Seniority Detection ---
SENIORITY_PATTERNS = {
    'Junior': ['junior', 'entry', 'trainee', 'intern', 'graduate', 'absolvent', 
               '0-2 let', '1-2 roky', 'začátečník', 'entry-level'],
    'Mid': ['mid', 'regular', '2-5 let', '3-5 let', '2+ let', 'medior'],
    'Senior': ['senior', 'experienced', 'sr.', '5+ let', '5-10 let', 'zkušený', 
               'pokročilý', 'specialist'],
    'Lead': ['lead', 'principal', 'staff', 'architect', 'tech lead', 'team lead', 
             'vedoucí týmu', 'chapter lead'],
    'Executive': ['head of', 'director', 'vp', 'chief', 'cto', 'ceo', 'cfo', 'coo',
                  'ředitel', 'c-level', 'executive']
}

def classify_role(title: str, description: str = "") -> str:
    """Classify job into role category based on title and description."""
    text = f"{title} {description}".lower()
    
    # Priority: Check title first (more accurate), then description
    for role, keywords in ROLE_TAXONOMY.items():
        if any(kw in title.lower() for kw in keywords):
            return role
    
    # Fallback: Check description
    for role, keywords in ROLE_TAXONOMY.items():
        if any(kw in text for kw in keywords):
            return role
    
    return 'Other'

def detect_seniority(title: str, description: str = "") -> str:
    """Detect seniority level from title and description."""
    text = f"{title} {description}".lower()
    
    # Priority order: Executive > Lead > Senior > Junior > Mid (default)
    priority_order = ['Executive', 'Lead', 'Senior', 'Junior', 'Mid']
    
    for level in priority_order:
        patterns = SENIORITY_PATTERNS[level]
        if any(p in text for p in patterns):
            return level
    
    return 'Mid'  # Default to Mid if unclear

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
    location: str = "Czechia"


def normalize_text(text: str) -> str:
    """Normalize text by removing Unicode variations and thousand separators."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    # Remove dots used as thousand separators, standardizing digits (using compiled pattern)
    text = THOUSAND_SEP_PATTERN.sub(r"\1\2", text)
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

    def add_signal(self, signal: JobSignal):
        """Adds a new signal with semantic enrichment and HR classification."""
        # Calculate semantic metrics
        tox = SemanticEngine.analyze_toxicity(signal.description)
        tech = SemanticEngine.analyze_tech_lag(signal.description)
        h = get_content_hash(
            signal.title, signal.company, signal.description
        )

        # v1.0 HR Intelligence: Role and Seniority classification
        role = classify_role(signal.title, signal.description)
        seniority = detect_seniority(signal.title, signal.description)

        # Robust Salary Parsing
        _, _, avg_sal = self._parse_salary(signal.salary)

        now = datetime.now()
        try:
            self.con.execute(
                """
                INSERT OR IGNORE INTO signals 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    role,
                    seniority,
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
        s = s.lower().replace(" ", "").replace(" ", "")
        s = re.sub(r'(\d)\.(\d{3})', r'', s)  # Remove thousand separators only
        # Use compiled regex pattern for performance
        
        # Detect and convert hourly rates to monthly (160 hours/month standard)
        if '/hod' in s or '/h' in s or 'hodinu' in s or 'per hour' in s:
            nums_raw = [int(n) for n in SALARY_DIGITS_PATTERN.findall(s)]
            nums = [n * 160 if n < 1000 else n for n in nums_raw]  # Convert hourly to monthly
        else:
            nums = [int(n) for n in SALARY_DIGITS_PATTERN.findall(s) if int(n) > 1000]
        
        # Handle EUR conversion to CZK (approximate rate)
        if "eur" in s:
            nums = [n * 25 for n in nums]
        
        
        # Distinguish between NULL (missing), 0 (unpaid), and negotiable
        original_text = s  # Keep original for special case detection
        
        # Check for unpaid internships
        if 'unpaid' in original_text or '0czk' in original_text or '0kč' in original_text:
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
            # Log warning but still return the value
            import logging
            logging.debug(f"Suspicious salary detected: {avg_sal} CZK from '{original_text}'")
        
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
        """Re-runs semantic analysis and HR classification on all existing records."""
        print("Re-analyzing all stored signals with v1.0 HR Intelligence...")
        rows = self.con.execute("SELECT hash, title, description FROM signals").fetchall()
        for h, title, desc in rows:
            tox = SemanticEngine.analyze_toxicity(desc)
            tech = SemanticEngine.analyze_tech_lag(desc)
            role = classify_role(title or "", desc or "")
            seniority = detect_seniority(title or "", desc or "")
            self.con.execute(
                "UPDATE signals SET toxicity_score = ?, tech_status = ?, role_type = ?, seniority_level = ? WHERE hash = ?",
                [tox, tech, role, seniority, h]
            )
        # Invalidate cache after updates
        self.load_as_df()
        print(f"v1.0 Migration complete: {len(rows)} signals updated with role/seniority.")

    def vacuum_database(self):
        """Compact database to reclaim space from deleted records."""
        try:
            print("Compacting database (VACUUM)...")
            self.con.execute("VACUUM")
            print("Database compaction complete.")
        except Exception as e:
            print(f"Warning: VACUUM failed: {e}")

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

    # --- v1.0 HR INTELLIGENCE METHODS ---
    
    def get_role_distribution(self) -> pd.DataFrame:
        """Get job distribution by role type."""
        return self.df['role_type'].value_counts().reset_index()
    
    def get_seniority_distribution(self) -> pd.DataFrame:
        """Get job distribution by seniority level."""
        return self.df['seniority_level'].value_counts().reset_index()
    
    def get_salary_by_role(self) -> pd.DataFrame:
        """Get median salary breakdown by role type."""
        valid_sal = self.df[self.df['avg_salary'] > 0]
        result = valid_sal.groupby('role_type').agg(
            median_salary=('avg_salary', 'median'),
            count=('avg_salary', 'count')
        ).sort_values('median_salary', ascending=False).reset_index()
        return result[result['count'] >= 5]  # Minimum sample size
    
    def get_salary_by_seniority(self) -> pd.DataFrame:
        """Get median salary breakdown by seniority level."""
        valid_sal = self.df[self.df['avg_salary'] > 0]
        result = valid_sal.groupby('seniority_level').agg(
            median_salary=('avg_salary', 'median'),
            count=('avg_salary', 'count')
        ).reset_index()
        # Order by seniority progression
        order = ['Junior', 'Mid', 'Senior', 'Lead', 'Executive']
        result['order'] = result['seniority_level'].apply(lambda x: order.index(x) if x in order else 99)
        return result.sort_values('order').drop('order', axis=1)

    def get_seniority_role_matrix(self) -> pd.DataFrame:
        """Cross-analysis: Median salary by Seniority + Role (for data quality insights)."""
        valid_sal = self.df[self.df['avg_salary'] > 0]

        # Get top roles
        top_roles = valid_sal['role_type'].value_counts().head(6).index

        # Filter and pivot
        filtered = valid_sal[valid_sal['role_type'].isin(top_roles)]

        matrix = filtered.groupby(['seniority_level', 'role_type']).agg(
            median_salary=('avg_salary', 'median'),
            count=('avg_salary', 'count')
        ).reset_index()

        # Filter out small samples
        matrix = matrix[matrix['count'] >= 5]

        return matrix.sort_values(['role_type', 'median_salary'], ascending=[True, False])
    
    def get_skill_premiums(self) -> pd.DataFrame:
        """Calculate salary premium for top skills (v1.0 HR Intelligence) - using accurate patterns."""
        # Use skill_patterns from taxonomy for accurate detection
        skill_patterns = TAXONOMY.get('skill_patterns', {})

        # Focus on most common skills
        priority_skills = ['Python', 'JavaScript', 'TypeScript', 'Java', 'Go', 'Rust',
                           'React', 'Angular', 'Vue', 'Node.js', '.NET', 'Spring',
                           'SQL', 'MongoDB', 'Redis', 'Docker', 'Kubernetes',
                           'AWS', 'Azure', 'GCP', 'AI/ML']

        valid_sal = self.df[self.df['avg_salary'] > 0]
        if valid_sal.empty:
            return pd.DataFrame(columns=['Skill', 'Median', 'Premium', 'Jobs'])

        baseline_median = valid_sal['avg_salary'].median()

        premiums = []
        for skill_name in priority_skills:
            if skill_name not in skill_patterns:
                continue

            pattern = skill_patterns[skill_name]
            try:
                # Use regex pattern matching for accuracy
                mask = valid_sal['description'].fillna('').str.lower().str.contains(pattern, regex=True, case=False, na=False)
                skill_median = valid_sal[mask]['avg_salary'].median()
                count = mask.sum()

                if pd.notna(skill_median) and count >= 10:
                    premium_pct = ((skill_median / baseline_median) - 1) * 100
                    premiums.append({
                        'Skill': skill_name,
                        'Median': int(skill_median),
                        'Premium': f"+{int(premium_pct)}%" if premium_pct >= 0 else f"{int(premium_pct)}%",
                        'Premium_Raw': premium_pct,
                        'Jobs': int(count)
                    })
            except Exception as e:
                # Fallback to simple matching if regex fails
                import logging
                logging.debug(f"Regex failed for {skill_name}, using fallback: {e}")
                mask = valid_sal['description'].fillna('').str.lower().str.contains(skill_name.lower(), regex=False)
                skill_median = valid_sal[mask]['avg_salary'].median()
                count = mask.sum()
                if pd.notna(skill_median) and count >= 10:
                    premium_pct = ((skill_median / baseline_median) - 1) * 100
                    premiums.append({
                        'Skill': skill_name,
                        'Median': int(skill_median),
                        'Premium': f"+{int(premium_pct)}%" if premium_pct >= 0 else f"{int(premium_pct)}%",
                        'Premium_Raw': premium_pct,
                        'Jobs': int(count)
                    })

        if not premiums:
            return pd.DataFrame(columns=['Skill', 'Median', 'Premium', 'Jobs'])

        return pd.DataFrame(premiums).sort_values('Premium_Raw', ascending=False).drop('Premium_Raw', axis=1)

    # --- v1.1 BENEFITS INTELLIGENCE ---

    def get_benefits_analysis(self) -> pd.DataFrame:
        """Analyze which benefits are most commonly offered."""
        benefits_cats = TAXONOMY.get('benefits_keywords', {})

        # User-friendly display names
        benefit_display_names = {
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

        results = []
        for benefit_name, keywords in benefits_cats.items():
            pattern = '|'.join([re.escape(kw) for kw in keywords])
            mask = self.df['description'].fillna('').str.lower().str.contains(pattern, regex=True, case=False)
            count = mask.sum()
            percentage = (count / len(self.df)) * 100

            if count > 0:
                display_name = benefit_display_names.get(benefit_name, benefit_name.title())
                results.append({
                    'Benefit': display_name,
                    'Jobs': int(count),
                    'Percentage': f"{percentage:.1f}%",
                    'Percentage_Raw': percentage
                })

        if not results:
            return pd.DataFrame(columns=['Benefit', 'Jobs', 'Percentage'])

        return pd.DataFrame(results).sort_values('Percentage_Raw', ascending=False).drop('Percentage_Raw', axis=1)

    def get_benefits_by_role(self) -> pd.DataFrame:
        """Show which roles get the best benefits (top 3 benefits)."""
        benefits_cats = TAXONOMY.get('benefits_keywords', {})

        # Count benefits per job
        def count_benefits(desc):
            if not isinstance(desc, str):
                return 0
            desc_lower = desc.lower()
            count = 0
            for keywords in benefits_cats.values():
                pattern = '|'.join([re.escape(kw) for kw in keywords])
                if re.search(pattern, desc_lower):
                    count += 1
            return count

        self.df['benefit_count'] = self.df['description'].apply(count_benefits)

        result = self.df.groupby('role_type').agg(
            avg_benefits=('benefit_count', 'mean'),
            count=('role_type', 'count')
        ).sort_values('avg_benefits', ascending=False).reset_index()

        # Clean up temp column
        self.df.drop('benefit_count', axis=1, inplace=True, errors='ignore')

        return result[result['count'] >= 10].head(8)  # Top 8 roles with enough samples

    # --- v1.1 LOCATION INTELLIGENCE ---

    def get_salary_by_city(self) -> pd.DataFrame:
        """Get median salary breakdown by city/location."""
        valid_sal = self.df[self.df['avg_salary'] > 0]

        # Get top cities by job count
        top_cities = valid_sal['city'].value_counts().head(10).index
        city_data = valid_sal[valid_sal['city'].isin(top_cities)]

        result = city_data.groupby('city').agg(
            median_salary=('avg_salary', 'median'),
            count=('avg_salary', 'count')
        ).sort_values('median_salary', ascending=False).reset_index()

        return result[result['count'] >= 20]  # Minimum 20 samples

    def get_location_distribution(self) -> pd.DataFrame:
        """Get job distribution by location."""
        top_cities = self.df['city'].value_counts().head(10).reset_index()
        top_cities.columns = ['City', 'Count']
        return top_cities

    # --- v1.1 WORK MODEL INTELLIGENCE ---

    def get_work_model_distribution(self) -> dict:
        """Classify jobs by work model: Remote, Hybrid, Office."""
        work_model_kw = TAXONOMY.get('work_model_keywords', {})

        remote_pattern = '|'.join(work_model_kw.get('remote', []))
        hybrid_pattern = '|'.join(work_model_kw.get('hybrid', []))

        desc = self.df['description'].fillna('').str.lower()

        # Priority: Remote > Hybrid > Office
        is_remote = desc.str.contains(remote_pattern, case=False, na=False, regex=True)
        is_hybrid = desc.str.contains(hybrid_pattern, case=False, na=False, regex=True) & ~is_remote

        remote_count = is_remote.sum()
        hybrid_count = is_hybrid.sum()
        office_count = len(self.df) - remote_count - hybrid_count

        return {
            "Full Remote": int(remote_count),
            "Hybrid": int(hybrid_count),
            "Office Only": int(office_count)
        }

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
        """Calculate salary premium for remote vs office jobs."""
        work_model_kw = TAXONOMY.get('work_model_keywords', {})
        remote_pattern = '|'.join(work_model_kw.get('remote', []))

        valid_sal = self.df[self.df['avg_salary'] > 0]
        desc = valid_sal['description'].fillna('').str.lower()

        is_remote = desc.str.contains(remote_pattern, case=False, na=False, regex=True)

        remote_median = valid_sal[is_remote]['avg_salary'].median()
        office_median = valid_sal[~is_remote]['avg_salary'].median()

        if pd.notna(remote_median) and pd.notna(office_median) and office_median > 0:
            premium_pct = int(((remote_median / office_median) - 1) * 100)
            return {
                'remote_median': int(remote_median),
                'office_median': int(office_median),
                'premium': f"+{premium_pct}%" if premium_pct >= 0 else f"{premium_pct}%",
                'premium_raw': premium_pct
            }

        return {'remote_median': 0, 'office_median': 0, 'premium': 'N/A', 'premium_raw': 0}

    # --- v1.2 TEMPORAL & EMERGING TRENDS ---

    def get_salary_trend_weekly(self) -> pd.DataFrame:
        """
        Get weekly median salary trends (requires 7+ days of data).
        Returns empty DataFrame if insufficient data.
        """
        import pandas as pd

        df_with_dates = self.df.copy()
        df_with_dates['scraped_date'] = pd.to_datetime(df_with_dates['scraped_at']).dt.date

        unique_dates = df_with_dates['scraped_date'].nunique()

        if unique_dates < 7:
            return pd.DataFrame(columns=['week', 'median_salary', 'count'])

        valid_sal = df_with_dates[df_with_dates['avg_salary'] > 0]
        valid_sal['week'] = pd.to_datetime(valid_sal['scraped_at']).dt.to_period('W')

        trend = valid_sal.groupby('week').agg(
            median_salary=('avg_salary', 'median'),
            count=('avg_salary', 'count')
        ).reset_index()

        trend['week'] = trend['week'].astype(str)
        return trend

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
        result['Company'] = result['Company'].apply(lambda x: ' '.join(x.lstrip('•\u2022\u2023\u25E6\u25AA\u25AB').strip().split()))

        return result

    def get_trending_benefits(self) -> pd.DataFrame:
        """
        Show fastest-growing benefits (based on frequency).
        For single-day data, this shows current hot benefits.
        """
        benefits_cats = TAXONOMY.get('benefits_keywords', {})

        benefit_display_names = {
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
            'cafeteria': 'Flexible Benefits'
        }

        results = []
        for benefit_name, keywords in benefits_cats.items():
            pattern = '|'.join([re.escape(kw) for kw in keywords])
            mask = self.df['description'].fillna('').str.lower().str.contains(pattern, regex=True, case=False)
            count = mask.sum()
            percentage = (count / len(self.df)) * 100

            if count >= 100:  # Minimum threshold
                display_name = benefit_display_names.get(benefit_name, benefit_name.title())
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
        Calculate the IČO (contractor) vs HPP (employee) salary premium.
        Reveals tax optimization pressure.
        """
        valid_sal = self.df[self.df['avg_salary'] > 0]

        # Classify by contract type
        ico_pattern = '|'.join(TAXONOMY['contract_keywords']['ico'])
        brigada_pattern = '|'.join(TAXONOMY['contract_keywords']['brigada'])

        desc = valid_sal['description'].fillna('').str.lower()

        is_ico = desc.str.contains(ico_pattern, case=False, na=False, regex=True)
        is_brigada = desc.str.contains(brigada_pattern, case=False, na=False, regex=True)

        # HPP is everything that's NOT IČO or Brigáda
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
        rigid_signals = r'2 days?\s+(?:office|kancelář)|fixed days?|povinná přítomnost|mandatory office|3\s*days?\s*week'
        flexible_signals = r'flexible|volně|kdykoliv|come if you want|podle potřeby|flexibilní'

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
        ai_pattern = r'\bai\b|\bchatgpt\b|\bgpt\b|\bmachine learning\b|\bml\b|\bgenerat|\bart.*inteligence'

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
        ghosts['Company'] = ghosts['Company'].apply(lambda x: ' '.join(x.lstrip('•\u2022\u2023\u25E6\u25AA\u25AB').strip().split()))

        return ghosts