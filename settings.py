"""
Centralized configuration settings for JobsCzInsight.
All paths and environment-specific settings should be defined here.
"""
from pathlib import Path
from typing import Optional
import os


class Settings:
    """Centralized configuration for the HR Intelligence system."""
    
    # --- Base Paths ---
    BASE_DIR: Path = Path(__file__).parent
    DATA_DIR: Path = BASE_DIR / "data"
    CONFIG_DIR: Path = BASE_DIR / "config"
    TEMPLATES_DIR: Path = BASE_DIR / "templates"
    PUBLIC_DIR: Path = BASE_DIR / "public"
    
    # --- Database ---
    DB_PATH: Path = DATA_DIR / "intelligence.db"
    DB_BACKUP_PATH: Path = DATA_DIR / "intelligence.db.backup"
    
    # --- Cache ---
    LLM_CACHE_PATH: Path = DATA_DIR / "llm_cache.json"
    
    # --- Config Files ---
    TAXONOMY_PATH: Path = CONFIG_DIR / "taxonomy.yaml"
    SELECTORS_PATH: Path = CONFIG_DIR / "selectors.yaml"
    CURRENCY_RATES_PATH: Path = CONFIG_DIR / "currency_rates.yaml"
    
    # --- Output ---
    REPORT_HTML_PATH: Path = PUBLIC_DIR / "report.html"
    DASHBOARD_HTML_PATH: Path = PUBLIC_DIR / "executive_dashboard.html"
    
    # --- Environment Overrides ---
    @classmethod
    def get_db_path(cls) -> Path:
        """Get DB path, allowing override via environment variable."""
        env_path = os.environ.get("JOBSCZINSIGHT_DB_PATH")
        return Path(env_path) if env_path else cls.DB_PATH
    
    @classmethod
    def get_cache_path(cls) -> Path:
        """Get cache path, allowing override via environment variable."""
        env_path = os.environ.get("JOBSCZINSIGHT_CACHE_PATH")
        return Path(env_path) if env_path else cls.LLM_CACHE_PATH
    
    @classmethod
    def ensure_dirs(cls) -> None:
        """Ensure all required directories exist."""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.CONFIG_DIR.mkdir(exist_ok=True)
        cls.PUBLIC_DIR.mkdir(exist_ok=True)


# Convenience accessor
settings = Settings()
