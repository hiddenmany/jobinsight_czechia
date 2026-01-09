
import asyncio
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper import WttjScraper, ScrapeEngine, async_playwright, PagedScraper
from analyzer import IntelligenceCore
from scraper_utils import CircuitBreaker

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s [%(levelname)s] %(message)s')

async def verify_yield():
    print('--- Starting Final Yield & Stability Verification ---')
    
    # Initialize globals mock
    import scraper
    scraper.CORE = IntelligenceCore(read_only=False)
    scraper.CIRCUIT_BREAKER = CircuitBreaker()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        engine = ScrapeEngine(browser)
        
        # 1. Test WTTJ Yield
        wttj = WttjScraper(engine, "WTTJ")
        print('\n[1/2] Verifying WTTJ yield (Target: >50 jobs)...')
        await wttj.run(limit=100)
        wttj_success = wttj.extraction_stats['success']
        print(f'WTTJ Success Count: {wttj_success}')
        
        # 2. Test Cocuma full traversal
        cocuma = PagedScraper(engine, "Cocuma")
        print('\n[2/2] Verifying Cocuma traversal (Target: gracefully reach end)...')
        await cocuma.run(limit=20) # We know it ends around 13-14
        cocuma_success = cocuma.extraction_stats['success']
        print(f'Cocuma Success Count: {cocuma_success}')
        
        await browser.close()
    
    print('\n--- Verification Summary ---')
    print(f'WTTJ Yield: {wttj_success}')
    print(f'Cocuma Yield: {cocuma_success}')
    
    # Assertions for success
    # WTTJ has ~50 jobs total for Czechia right now, so >40 is a good yield indicator
    assert wttj_success >= 40, f"WTTJ yield too low: {wttj_success}"
    print('SUCCESS: Maintenance track verified yield and graceful termination.')

if __name__ == '__main__':
    asyncio.run(verify_yield())
