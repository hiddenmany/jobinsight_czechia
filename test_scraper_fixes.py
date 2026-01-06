"""Quick validation test for StartupJobs and WTTJ scraper fixes.
Tests with fresh database state to avoid is_known() filtering all jobs.
"""
import asyncio
import os
import sys
import time
import shutil

# Temporarily rename database to test with fresh state
DB_PATH = 'data/intelligence.db'
DB_BACKUP = 'data/intelligence.db.test_backup'

def backup_db():
    if os.path.exists(DB_PATH):
        # Use shutil.move which handles locks better
        for attempt in range(3):
            try:
                shutil.move(DB_PATH, DB_BACKUP)
                print(f"Backed up database to {DB_BACKUP}")
                return True
            except (PermissionError, OSError) as e:
                print(f"Backup attempt {attempt+1} failed: {e}")
                time.sleep(1)
        print("Could not backup database, running without backup")
        return False
    return True

def restore_db():
    if os.path.exists(DB_BACKUP):
        for attempt in range(3):
            try:
                if os.path.exists(DB_PATH):
                    os.remove(DB_PATH)
                shutil.move(DB_BACKUP, DB_PATH)
                print(f"Restored database from {DB_BACKUP}")
                return
            except (PermissionError, OSError) as e:
                print(f"Restore attempt {attempt+1} failed: {e}")
                time.sleep(1)
        print("Could not restore database")

async def test():
    import scraper
    from scraper import StartupJobsScraper, WttjScraper, ScrapeEngine, IntelligenceCore, CircuitBreaker
    from playwright.async_api import async_playwright
    
    # Initialize globals for the scraper module
    scraper.CORE = IntelligenceCore()
    scraper.CIRCUIT_BREAKER = CircuitBreaker(failure_threshold=5, timeout_seconds=300)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        engine = ScrapeEngine(browser)
        
        print('=== Testing StartupJobs (target: 200 jobs) ===')
        sj = StartupJobsScraper(engine, 'StartupJobs')
        await sj.run(limit=200)
        print(f'StartupJobs result: {sj.extraction_stats}')
        
        print('\n=== Testing WTTJ (target: 200 jobs) ===')
        wttj = WttjScraper(engine, 'WTTJ')
        await wttj.run(limit=200)
        print(f'WTTJ result: {wttj.extraction_stats}')
        
        await browser.close()
        
        # Validation
        sj_success = sj.extraction_stats['success']
        wttj_success = wttj.extraction_stats['success']
        
        # Check salary coverage via DataFrame
        df = scraper.CORE.df
        sj_df = df[df['source'] == 'StartupJobs']
        wttj_df = df[df['source'] == 'WTTJ']
        
        sj_salaries = sj_df[sj_df['salary_raw'].notna() & (sj_df['salary_raw'] != "")]
        wttj_salaries = wttj_df[wttj_df['salary_raw'].notna() & (wttj_df['salary_raw'] != "")]
        
        print('\n=== SALARY COVERAGE ===')
        sj_count = len(sj_salaries)
        wttj_count = len(wttj_salaries)
        sj_total = len(sj_df)
        wttj_total = len(wttj_df)
        
        sj_perc = (sj_count / sj_total * 100) if sj_total > 0 else 0
        wttj_perc = (wttj_count / wttj_total * 100) if wttj_total > 0 else 0
        
        print(f'StartupJobs salaries: {sj_count}/{sj_total} ({sj_perc:.1f}%)')
        print(f'WTTJ salaries: {wttj_count}/{wttj_total} ({wttj_perc:.1f}%)')
        
        if sj_count > 0:
            print(f'Sample StartupJobs salary: {sj_salaries.iloc[0]["salary_raw"]}')
        
        print('\n=== VALIDATION ===')
        sj_ok = sj_success >= 40
        wttj_ok = wttj_success >= 50
        print(f'StartupJobs: {"PASS" if sj_ok else "FAIL"} ({sj_success} jobs, expected >= 40)')
        print(f'WTTJ: {"PASS" if wttj_ok else "FAIL"} ({wttj_success} jobs, expected >= 50)')
        
        return sj_ok and wttj_ok

if __name__ == "__main__":
    backed_up = backup_db()
    try:
        result = asyncio.run(test())
    finally:
        if backed_up:
            restore_db()
    
    sys.exit(0 if result else 1)
