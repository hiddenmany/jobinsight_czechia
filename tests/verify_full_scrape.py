
import asyncio
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper import StartupJobsScraper, ScrapeEngine, async_playwright
from analyzer import IntelligenceCore
from scraper_utils import CircuitBreaker, Heartbeat

# Configure logging to stdout to see heartbeats
logging.basicConfig(
    level=logging.INFO, 
    stream=sys.stdout, 
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Initialize globals mock
import scraper
scraper.CORE = IntelligenceCore(read_only=False)
scraper.CIRCUIT_BREAKER = CircuitBreaker()

async def verify_resilience():
    print('--- Starting Resilient Scrape Verification ---')
    print('Target: StartupJobs (Limit 60 - multiple batches)')
    
    # Override Heartbeat interval to be very short for this test
    # so we see it even in a short run
    import scraper_utils
    # Monkey patch Heartbeat to be faster for verification
    original_init = scraper_utils.Heartbeat.__init__
    def faster_init(self, interval=30.0, message="Heartbeat"):
        original_init(self, interval=5.0, message=message + " [FAST]")
    scraper_utils.Heartbeat.__init__ = faster_init

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        engine = ScrapeEngine(browser)
        scraper_inst = StartupJobsScraper(engine, 'StartupJobs')
        
        # We need to wrap this in the same way main() does to trigger the heartbeat
        # But StartupJobsScraper doesn't have the heartbeat inside .run(), 
        # it's wrapped AROUND .run() in main().
        # So we replicate that structure here.
        
        with Heartbeat(interval=5.0, message="Scraping Batch 2: StartupJobs..."):
            await scraper_inst.run(limit=60)
            
        await browser.close()
    
    print('--- Verification Complete ---')

if __name__ == '__main__':
    asyncio.run(verify_resilience())
