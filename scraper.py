import asyncio
import random
import re
import logging
from dataclasses import dataclass
from typing import List, Optional

from playwright.async_api import async_playwright
from playwright_stealth import stealth
from tqdm.asyncio import tqdm

import analyzer
from analyzer import JobSignal, IntelligenceCore

# --- CONFIGURATION ---
CONCURRENCY = 5
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

    async def get_context(self):
        context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        return context

    async def intercept_noise(self, route):
        bad_patterns = ["google-analytics", "hotjar", "facebook", "pixel", "doubleclick"]
        if route.request.resource_type in ["image", "media", "font"]:
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
                for sel in ["button:has-text('Zobrazit více')", "button:has-text('Číst dál')", ".job-detail__description-button", "text=Read more"]:
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


class JobsCzScraper:
    """Specialized parser for Jobs.cz / Prace.cz logic."""
    
    def __init__(self, engine: ScrapeEngine):
        self.engine = engine

    async def run(self, name, base_url, card_sel, title_sel, limit=50):
        context = await self.engine.get_context()
        page = await context.new_page()
        pbar = tqdm(total=limit, desc=f"[*] {name}", unit="pg")

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
                    
                    # Better company extraction
                    company_el = await card.query_selector(".SearchResultCard__footerItem, [data-test='employer-name'], .search-result__advert__box__item--company")
                    company_name = await company_el.inner_text() if company_el else "Unknown Entity"
                    
                    link = await title_el.get_attribute("href")
                    if not link.startswith("http"):
                        link = ("https://www.jobs.cz" if "jobs" in base_url else "https://www.prace.cz") + link
                    
                    if CORE.is_known(link): continue

                    # Pre-extract salary
                    sal_el = await card.query_selector("span.Tag--success, .search-result__advert__box__item--salary")
                    
                    sig = JobSignal(
                        title=await title_el.inner_text(),
                        company="Market Signal",
                        link=link,
                        source=name,
                        salary=await sal_el.inner_text() if sal_el else None
                    )
                    batch.append(sig)

                if batch:
                    await asyncio.gather(*(self.engine.scrape_detail(context, s) for s in batch))
                    for s in batch: CORE.add_signal(s)
                
                pbar.update(1)
                if not batch and page_num > 5: break
            except Exception as e:
                logger.debug(f"Error in {name} loop: {e}")
                break
        
        await context.close()


class StartupJobsScraper:
    def __init__(self, engine: ScrapeEngine):
        self.engine = engine

    async def run(self, limit=500):
        name = "StartupJobs"
        context = await self.engine.get_context()
        page = await context.new_page()
        await page.goto("https://www.startupjobs.cz/nabidky")
        try: await page.get_by_text("Přijmout").click(timeout=5000)
        except: pass
        
        pbar = tqdm(total=limit, desc=f"[*] {name}", unit="ads")
        last_count = 0
        while last_count < limit:
            await page.keyboard.press("End")
            await asyncio.sleep(2)
            cards = await page.query_selector_all("a[href*='/nabidka/']")
            if len(cards) == last_count: break
            pbar.update(min(len(cards) - last_count, limit - last_count))
            last_count = len(cards)
        
        cards = await page.query_selector_all("a[href*='/nabidka/']")
        batch = []
        for card in cards[:limit]:
            link = "https://www.startupjobs.cz" + await card.get_attribute("href")
            if CORE.is_known(link): continue
            
            salary = None
            items = await card.query_selector_all("li")
            for item in items:
                txt = await item.inner_text()
                if "Kč" in txt or "EUR" in txt:
                    salary = txt.strip()
                    break

            sig = JobSignal(
                title=(await card.inner_text()).split("\n")[0],
                company="Startup",
                link=link,
                source=name,
                salary=salary
            )
            batch.append(sig)
        
        if batch:
            await asyncio.gather(*(self.engine.scrape_detail(context, s) for s in batch))
            for s in batch: CORE.add_signal(s)
            
        await context.close()


class WttjScraper:
    def __init__(self, engine: ScrapeEngine):
        self.engine = engine

    async def run(self, limit=200):
        name = "WTTJ"
        context = await self.engine.get_context()
        page = await context.new_page()
        await page.goto("https://www.welcometothejungle.com/cs/jobs?aroundQuery=Czechia")
        pbar = tqdm(total=limit, desc=f"[*] {name}", unit="ads")
        for _ in range(20): 
            await page.keyboard.press("PageDown")
            await asyncio.sleep(1)
        
        cards = await page.query_selector_all("li.ais-Hits-item")
        batch = []
        for card in cards[:limit]:
            try:
                link_el = await card.query_selector("a")
                link = "https://www.welcometothejungle.com" + await link_el.get_attribute("href")
                if CORE.is_known(link): continue
                sig = JobSignal(
                    title=await (await card.query_selector("h4")).inner_text(),
                    company="WTTJ Partner",
                    link=link,
                    source=name
                )
                batch.append(sig)
                pbar.update(1)
            except: continue
        
        if batch:
            await asyncio.gather(*(self.engine.scrape_detail(context, s) for s in batch))
            for s in batch: CORE.add_signal(s)
        await context.close()


class CocumaScraper:
    def __init__(self, engine: ScrapeEngine):
        self.engine = engine

    async def run(self, limit=20):
        name = "Cocuma"
        context = await self.engine.get_context()
        page = await context.new_page()
        pbar = tqdm(total=limit, desc=f"[*] {name}", unit="pg")
        for page_num in range(1, limit + 1):
            try:
                await page.goto(f"https://www.cocuma.cz/jobs/?page={page_num}/")
                cards = await page.query_selector_all("a.job-thumbnail")
                if not cards: break
                batch = []
                for card in cards:
                    link = "https://www.cocuma.cz" + await card.get_attribute("href")
                    if CORE.is_known(link): continue
                    sig = JobSignal(
                        title=await (await card.query_selector(".job-thumbnail-title")).inner_text(),
                        company=await (await card.query_selector(".job-thumbnail-company")).inner_text(),
                        link=link,
                        source=name
                    )
                    batch.append(sig)
                if batch:
                    await asyncio.gather(*(self.engine.scrape_detail(context, s) for s in batch))
                    for s in batch: CORE.add_signal(s)
                pbar.update(1)
            except: break
        await context.close()


class LinkedinScraper:
    def __init__(self, engine: ScrapeEngine):
        self.engine = engine

    async def run(self, limit=100):
        name = "LinkedIn"
        context = await self.engine.get_context()
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/jobs/search?keywords=&location=Czechia")
        pbar = tqdm(total=limit, desc=f"[*] {name}", unit="ads")
        for _ in range(15):
            await page.keyboard.press("End")
            await asyncio.sleep(2)
        cards = await page.query_selector_all("div.base-card")
        for card in cards[:limit]:
            try:
                link = (await (await card.query_selector("a")).get_attribute("href")).split('?')[0]
                if CORE.is_known(link): continue
                CORE.add_signal(JobSignal(
                    title=await (await card.query_selector("h3")).inner_text(),
                    company=await (await card.query_selector("h4")).inner_text(),
                    link=link,
                    source=name,
                    description="LinkedIn Market Signal"
                ))
                pbar.update(1)
            except: continue
        await context.close()


async def main():
    logger.info("--- OMNISCRAPE v6.1: INCREMENTAL SYNC MODE ---")
    
    # Ensure schema is up to date (DuckDB doesn't do migrations easily, so we try to add the column)
    try:
        CORE.con.execute("ALTER TABLE signals ADD COLUMN last_seen_at TIMESTAMP")
    except:
        pass # Column likely exists

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        engine = ScrapeEngine(browser)
        
        # Scrapers
        jobs_cz = JobsCzScraper(engine)
        startup = StartupJobsScraper(engine)
        wttj = WttjScraper(engine)
        cocuma = CocumaScraper(engine)
        linkedin = LinkedinScraper(engine)
        
        await asyncio.gather(
            jobs_cz.run("Jobs.cz", "https://www.jobs.cz/prace/?page=", "article.SearchResultCard", "h2.SearchResultCard__title > a", limit=50),
            jobs_cz.run("Prace.cz", "https://www.prace.cz/nabidky/?page=", "li.search-result__advert", "a.link", limit=50),
            startup.run(limit=500),
            wttj.run(limit=200),
            cocuma.run(limit=10),
            linkedin.run(limit=100)
        )
        
        await browser.close()
    
    # Post-scrape cleanup
    CORE.cleanup_expired(threshold_minutes=30)
    logger.info("--- INTEL CORE SYNCHRONIZED ---")

if __name__ == "__main__":
    # Migration: Update existing data if requested
    CORE.reanalyze_all()
    asyncio.run(main())