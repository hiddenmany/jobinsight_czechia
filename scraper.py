import asyncio
import random
import re
import logging
import yaml
import os
from dataclasses import dataclass
from typing import List, Optional, Dict

from playwright.async_api import async_playwright
from playwright_stealth import stealth
from tqdm.asyncio import tqdm

import analyzer
from analyzer import JobSignal, IntelligenceCore

# --- CONFIGURATION ---
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "selectors.yaml")
with open(CONFIG_PATH, 'r') as f:
    CONFIG = yaml.safe_load(f)

CONCURRENCY = 10
CORE = IntelligenceCore()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("scraper.log"), logging.StreamHandler()]
)
logger = logging.getLogger("OmniScrape")


class ScrapeEngine:
    """The heavy-duty engine that handles browser lifecycle and concurrency."""

    def __init__(self, browser):
        self.browser = browser
        self.semaphore = asyncio.Semaphore(CONCURRENCY)
        self.common_config = CONFIG.get('common', {})

    async def get_context(self):
        context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        return context

    async def intercept_noise(self, route):
        noise_cfg = self.common_config.get('intercept_noise', {})
        bad_patterns = noise_cfg.get('bad_patterns', [])
        resource_types = noise_cfg.get('resource_types', [])
        
        if route.request.resource_type in resource_types:
            await route.abort()
        elif any(p in route.request.url for p in bad_patterns):
            await route.abort()
        else:
            await route.continue_()

    async def scrape_detail(self, context, signal: JobSignal):
        """Fetches the full JD and benefits for a signal."""
        if not signal.link or "linkedin.com" in signal.link:
            return

        async with self.semaphore:
            page = await context.new_page()
            try:
                if callable(stealth):
                    await stealth(page)
                await page.route("**/*", self.intercept_noise)
                await page.goto(signal.link, timeout=30000, wait_until="domcontentloaded")

                # Expand "Read More"
                buttons = self.common_config.get('read_more_buttons', [])
                for sel in buttons:
                    try:
                        btn = page.locator(sel)
                        if await btn.is_visible():
                            await btn.click(force=True)
                            await asyncio.sleep(0.5)
                    except: pass

                # Extraction logic
                signal.description = await page.evaluate("""() => {
                    const s = ['div.JobDescription', 'article', 'main', '.jd-content', '.job-detail__description'];
                    for (let x of s) { let el = document.querySelector(x); if (el) return el.innerText; }
                    return document.body.innerText;
                }""")
                
                signal.benefits = await page.evaluate("""() => {
                    const tags = Array.from(document.querySelectorAll('.benefit-item, .Tag--success, .Badge--success, [data-test*="benefit"]'));
                    return tags.map(t => t.innerText.trim()).filter(t => t.length > 1).join(', ');
                }""")

                signal.description = signal.description.strip()[:5000]
                await page.close()
            except Exception as e:
                logger.debug(f"Failed detail fetch for {signal.link}: {e}")
                await page.close()


class BaseScraper:
    """Base class for all site-specific scrapers."""
    def __init__(self, engine: ScrapeEngine, site_name: str):
        self.engine = engine
        self.site_name = site_name
        self.config = CONFIG.get('scrapers', {}).get(site_name, {})

    async def run(self, limit: int):
        raise NotImplementedError

    async def extract_company(self, card):
        selectors = self.config.get('company_selectors', [])
        if not selectors and 'company' in self.config:
            selectors = [self.config['company']]
            
        for sel in selectors:
            el = await card.query_selector(sel)
            if el:
                txt = (await el.inner_text()).strip()
                if txt and len(txt) > 1:
                    return txt
        return "Unknown Employer"


class PagedScraper(BaseScraper):
    """Handles scrapers with numbered pagination (Jobs.cz, Prace.cz, Cocuma)."""
    async def run(self, limit=50):
        context = await self.engine.get_context()
        page = await context.new_page()
        pbar = tqdm(total=limit, desc=f"[*] {self.site_name}", unit="pg")

        base_url = self.config.get('base_url')
        card_sel = self.config.get('card')
        title_sel = self.config.get('title')

        for page_num in range(1, limit + 1):
            try:
                await page.goto(f"{base_url}{page_num}", timeout=60000)
                await page.wait_for_selector(card_sel, timeout=10000)
                cards = await page.query_selector_all(card_sel)
                if not cards: break

                batch = []
                for card in cards:
                    title_el = await card.query_selector(title_sel)
                    if not title_el: continue
                    
                    company_name = await self.extract_company(card)
                    
                    link = await title_el.get_attribute("href")
                    if not link.startswith("http"):
                        domain = "https://www.jobs.cz" if "jobs" in base_url else "https://www.prace.cz"
                        if "cocuma" in base_url: domain = "https://www.cocuma.cz"
                        link = domain + link
                    
                    if CORE.is_known(link): continue

                    # Salary
                    salary = None
                    sal_sel = self.config.get('salary')
                    if sal_sel:
                        sal_el = await card.query_selector(sal_sel)
                        salary = await sal_el.inner_text() if sal_el else None
                    
                    sig = JobSignal(
                        title=await title_el.inner_text(),
                        company=company_name,
                        link=link,
                        source=self.site_name,
                        salary=salary
                    )
                    batch.append(sig)

                if batch:
                    await asyncio.gather(*(self.engine.scrape_detail(context, s) for s in batch))
                    for s in batch: CORE.add_signal(s)
                
                pbar.update(1)
                if not batch and page_num > 5: break
            except Exception as e:
                logger.debug(f"Error in {self.site_name} loop: {e}")
                break
        
        await context.close()


class StartupJobsScraper(BaseScraper):
    async def run(self, limit=500):
        context = await self.engine.get_context()
        page = await context.new_page()
        try:
            await page.goto(self.config['base_url'], timeout=60000)
            try: await page.get_by_text("Přijmout").click(timeout=5000)
            except: pass
            
            pbar = tqdm(total=limit, desc=f"[*] {self.site_name}", unit="ads")
            last_count = 0
            card_sel = self.config['card']
            
            # Wait for content to load
            try:
                await page.wait_for_selector(card_sel, timeout=15000)
            except:
                logger.warning(f"{self.site_name}: Timed out waiting for {card_sel}")

            # Robust Infinite Scroll with Button Click
            for _ in range(50): 
                await page.keyboard.press("End")
                await asyncio.sleep(2)
                
                # Try to click "Load more" button if it exists
                try:
                    load_more = page.locator("button:has-text('Načíst další'), button:has-text('Zobrazit více'), a.more-jobs")
                    if await load_more.count() > 0 and await load_more.first.is_visible():
                        await load_more.first.click(force=True)
                        await asyncio.sleep(2)
                except: pass
                
                cards = await page.query_selector_all(card_sel)
                
                if len(cards) >= limit: break
                
                if len(cards) == last_count:
                    # If stuck, try scrolling up and down
                    await page.mouse.wheel(0, -500)
                    await asyncio.sleep(0.5)
                    await page.mouse.wheel(0, 500)
                    await asyncio.sleep(1)
                
                pbar.update(min(len(cards) - last_count, limit - last_count))
                last_count = len(cards)
            
            cards = await page.query_selector_all(card_sel)
            batch = []
            for card in cards[:limit]:
                try:
                    href = await card.get_attribute("href")
                    if not href: continue
                    
                    if href.startswith("http"):
                        link = href
                    elif "cocuma" in self.config['base_url']:
                        link = "https://www.cocuma.cz" + href
                    else:
                        link = "https://www.startupjobs.cz" + href

                    if CORE.is_known(link): continue
                    
                    company_name = await self.extract_company(card)

                    salary = None
                    # StartupJobs specific salary extraction attempt
                    txt = await card.inner_text()
                    match = re.search(r'(\d+(?:\s\d+)*)\s*–\s*(\d+(?:\s\d+)*)\s*(?:Kč|EUR)', txt)
                    if match:
                        salary = match.group(0)

                    sig = JobSignal(
                        title=(await card.inner_text()).split("\n")[0],
                        company=company_name,
                        link=link,
                        source=self.site_name,
                        salary=salary
                    )
                    batch.append(sig)
                except: continue
            
            if batch:
                await asyncio.gather(*(self.engine.scrape_detail(context, s) for s in batch))
                for s in batch: CORE.add_signal(s)
                
        except Exception as e:
            logger.error(f"StartupJobs failed: {e}")
            
        await context.close()


class WttjScraper(BaseScraper):
    async def run(self, limit=200):
        context = await self.engine.get_context()
        page = await context.new_page()
        # WTTJ is heavy, wait for commit first then load
        try:
            await page.goto(self.config['base_url'], timeout=60000, wait_until="commit")
            await page.wait_for_selector(self.config['card'], timeout=20000)
        except:
            logger.warning("WTTJ failed initial load")
            await context.close()
            return

        pbar = tqdm(total=limit, desc=f"[*] {self.site_name}", unit="ads")
        
        # Scroll loop
        for _ in range(40): 
            await page.keyboard.press("End")
            await asyncio.sleep(1.5)
        
        card_sel = self.config['card']
        cards = await page.query_selector_all(card_sel)
        batch = []
        for card in cards[:limit]:
            try:
                link_el = await card.query_selector(self.config['link'])
                if not link_el: continue
                
                link = "https://www.welcometothejungle.com" + await link_el.get_attribute("href")
                if CORE.is_known(link): continue
                
                company_name = await self.extract_company(card)
                
                title_el = await card.query_selector(self.config['title'])
                title = await title_el.inner_text() if title_el else "Unknown Role"

                sig = JobSignal(
                    title=title,
                    company=company_name,
                    link=link,
                    source=self.site_name
                )
                batch.append(sig)
                pbar.update(1)
            except Exception as e: 
                continue
        
        if batch:
            await asyncio.gather(*(self.engine.scrape_detail(context, s) for s in batch))
            for s in batch: CORE.add_signal(s)
        await context.close()


class LinkedinScraper(BaseScraper):
    async def run(self, limit=100):
        context = await self.engine.get_context()
        page = await context.new_page()
        await page.goto(self.config['base_url'])
        pbar = tqdm(total=limit, desc=f"[*] {self.site_name}", unit="ads")
        for _ in range(50):
            await page.keyboard.press("End")
            await asyncio.sleep(1.5)
        
        card_sel = self.config['card']
        cards = await page.query_selector_all(card_sel)
        for card in cards[:limit]:
            try:
                link = (await (await card.query_selector(self.config['link'])).get_attribute("href")).split('?')[0]
                if CORE.is_known(link): continue
                
                company_name = await self.extract_company(card)
                
                CORE.add_signal(JobSignal(
                    title=await (await card.query_selector(self.config['title'])).inner_text(),
                    company=company_name,
                    link=link,
                    source=self.site_name,
                    description="LinkedIn Market Signal"
                ))
                pbar.update(1)
            except: continue
        await context.close()


async def main():
    logger.info("--- OMNISCRAPE v7.0: STRATEGY PATTERN & CONFIG-DRIVEN ---")
    
    try:
        CORE.con.execute("ALTER TABLE signals ADD COLUMN last_seen_at TIMESTAMP")
    except:
        pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        engine = ScrapeEngine(browser)
        
        # Initialize scrapers via the new strategy pattern
        jobs_cz = PagedScraper(engine, "Jobs.cz")
        prace_cz = PagedScraper(engine, "Prace.cz")
        # Cocuma uses infinite scroll, so we switch it to the StartupJobs engine (which handles scroll)
        # We rename the class instance but use the StartupJobsScraper class logic
        cocuma = StartupJobsScraper(engine, "Cocuma") 
        startup = StartupJobsScraper(engine, "StartupJobs")
        wttj = WttjScraper(engine, "WTTJ")
        linkedin = LinkedinScraper(engine, "LinkedIn")
        
        await asyncio.gather(
            jobs_cz.run(limit=100),    # 100 pages * 20 ads = 2000
            prace_cz.run(limit=100),   # 100 pages * 20 ads = 2000
            startup.run(limit=500),
            wttj.run(limit=500),
            cocuma.run(limit=500),    # Will naturally stop at max available (~50)
            linkedin.run(limit=500)
        )
        
        await browser.close()
    
    # Increase threshold to 180 minutes to account for long scrape runs and prevent premature deletion
    CORE.cleanup_expired(threshold_minutes=180)
    logger.info("--- INTEL CORE SYNCHRONIZED ---")

if __name__ == "__main__":
    CORE.reanalyze_all()
    asyncio.run(main())
