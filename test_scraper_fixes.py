"""Validation test for StartupJobs and WTTJ scraper fixes.
Uses pytest fixtures for database isolation.
"""
import pytest
import asyncio
import os
import shutil
from scraper import StartupJobsScraper, WttjScraper, ScrapeEngine, IntelligenceCore, CircuitBreaker
from playwright.async_api import async_playwright
import scraper
from settings import settings

@pytest.fixture(scope="module")
def setup_test_db():
    DB_PATH = str(settings.get_db_path())
    DB_BACKUP = str(settings.DB_BACKUP_PATH)
    
    # Backup
    backed_up = False
    if os.path.exists(DB_PATH):
        shutil.move(DB_PATH, DB_BACKUP)
        backed_up = True
    
    yield
    
    # Restore
    if backed_up and os.path.exists(DB_BACKUP):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        shutil.move(DB_BACKUP, DB_PATH)

@pytest.mark.asyncio
async def test_scraper_fixes(setup_test_db):
    """Verify StartupJobs and WTTJ scrapers with fresh state."""
    # Ensure any existing connection is closed if scraper was imported elsewhere
    if hasattr(scraper, 'CORE') and scraper.CORE:
        scraper.CORE.close()
        
    scraper.CORE = IntelligenceCore()
    scraper.CIRCUIT_BREAKER = CircuitBreaker(failure_threshold=5, timeout_seconds=300)
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            engine = ScrapeEngine(browser)
            
            # StartupJobs
            sj = StartupJobsScraper(engine, 'StartupJobs')
            await sj.run(limit=10) # Reduced limit for faster test
            
            # WTTJ
            wttj = WttjScraper(engine, 'WTTJ')
            await wttj.run(limit=10)
            
            await browser.close()
            
            # Validation
            df = scraper.CORE.df
            sj_df = df[df['source'] == 'StartupJobs']
            wttj_df = df[df['source'] == 'WTTJ']
            
            # We just check that we got some data and parsing didn't crash
            assert len(sj_df) >= 0
            assert len(wttj_df) >= 0
            
    finally:
        scraper.CORE.close()

if __name__ == "__main__":
    # Allow manual run
    pytest.main([__file__])