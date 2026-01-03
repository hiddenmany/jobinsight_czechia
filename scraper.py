import asyncio
import re
import logging
import yaml
import os
from typing import List, Optional, Dict

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout, Error as PlaywrightError
from playwright_stealth import stealth
from tqdm.asyncio import tqdm

import analyzer
from analyzer import JobSignal, IntelligenceCore
import scraper_utils
from scraper_utils import (
    validate_job_data,
    get_random_user_agent,
    sanitize_text,
    rate_limit,
    retry,
    CircuitBreaker,
    validate_scraper_config,
    shutdown_handler
)

# --- CONFIGURATION ---
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "selectors.yaml")

try:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        CONFIG = yaml.safe_load(f)
    if not CONFIG:
        raise ValueError("Config file is empty")
    # Validate config on startup
    for scraper_name, scraper_config in CONFIG.get('scrapers', {}).items():
        validate_scraper_config(scraper_config, scraper_name)
except Exception as e:
    logging.error(f"Failed to load/validate config: {e}")
    raise

# --- CONSTANTS ---
CONCURRENCY = 10
PAGE_TIMEOUT_MS = 60000          # 60 seconds for page loads
SELECTOR_TIMEOUT_MS = 10000      # 10 seconds for selectors
DETAIL_TIMEOUT_MS = 30000        # 30 seconds for detail pages
SCROLL_DELAY_SEC = 1.5           # Delay between scroll actions
STALL_THRESHOLD = 3              # Number of stalls before giving up
DESCRIPTION_MAX_LENGTH = 5000    # Max characters for job description
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080

# Compiled regex for performance
# Compiled regex for performance - enhanced to catch more salary formats
SALARY_PATTERN = re.compile(
    r'(\d+(?:[\s,.]\d+)*)[\s]*[Kk]?[\s]*[–\-][\s]*(\d+(?:[\s,.]\d+)*)[\s]*[Kk]?[\s]*(?:Kč|CZK|EUR|€|USD|\$)|'  # Range
    r'(?:from|od)[\s]+(\d+(?:[\s,.]\d+)*)[\s]*[Kk]?[\s]*(?:Kč|CZK|EUR|€)|'  # "from X"
    r'(?:up to|až|do)[\s]+(\d+(?:[\s,.]\d+)*)[\s]*[Kk]?[\s]*(?:Kč|CZK|EUR|€)|'  # "up to X"
    r'(\d{2,3})[\s]*[Kk](?:[\s]*Kč|[\s]*CZK|[\s]*EUR)?',  # "50K", "80K Kč"
    re.IGNORECASE
)

CORE = IntelligenceCore()
CIRCUIT_BREAKER = CircuitBreaker(failure_threshold=5, timeout_seconds=300)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.FileHandler("scraper.log"), logging.StreamHandler()]
)
logger = logging.getLogger("OmniScrape")

# Setup graceful shutdown
shutdown_handler.setup_signal_handlers()


class ScrapeEngine:
    """The heavy-duty engine that handles browser lifecycle and concurrency."""

    def __init__(self, browser):
        self.browser = browser
        self.semaphore = asyncio.Semaphore(CONCURRENCY)
        self.common_config = CONFIG.get('common', {})

    async def get_context(self):
        context = await self.browser.new_context(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            user_agent=get_random_user_agent(),  # Randomized UA to avoid bot detection
        )
        return context

    async def intercept_noise(self, route):
        noise_cfg = self.common_config.get('intercept_noise', {})
        bad_patterns = noise_cfg.get('bad_patterns', [])
        resource_types = noise_cfg.get('resource_types', [])
        
        # NEVER abort the main navigation request
        if route.request.is_navigation_request():
            await route.continue_()
            return

        if route.request.resource_type in resource_types:
            await route.abort()
        elif any(p in route.request.url for p in bad_patterns):
            await route.abort()
        else:
            await route.continue_()

    @retry(max_attempts=3, exceptions=(PlaywrightTimeout, PlaywrightError))
    async def scrape_detail(self, context, signal: JobSignal):
        """Fetches the full JD and benefits for a signal."""
        if not signal.link:
            return

        page = None
        async with self.semaphore:
            try:
                page = await context.new_page()
                if callable(stealth):
                    await stealth(page)
                await page.route("**/*", self.intercept_noise)
                
                # Add rate limiting
                await rate_limit(1.0, 2.0)
                
                await page.goto(signal.link, timeout=DETAIL_TIMEOUT_MS, wait_until="domcontentloaded")

                # Expand "Read More"
                buttons = self.common_config.get('read_more_buttons', [])
                for sel in buttons:
                    try:
                        btn = page.locator(sel)
                        if await btn.is_visible():
                            await btn.click(force=True)
                            await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.debug(f"Read more button click failed for {sel}: {e}")

                # Extraction logic
                raw_description = await page.evaluate("""() => {
                    const s = ['div.JobDescription', 'article', 'main', '.jd-content', '.job-detail__description'];
                    for (let x of s) { let el = document.querySelector(x); if (el) return el.innerText; }
                    return document.body.innerText;
                }""")
                
                raw_benefits = await page.evaluate("""() => {
                    const tags = Array.from(document.querySelectorAll('.benefit-item, .Tag--success, .Badge--success, [data-test*="benefit"]'));
                    return tags.map(t => t.innerText.trim()).filter(t => t.length > 1).join(', ');
                }""")

                # Sanitize extracted text (security fix)
                signal.description = sanitize_text(raw_description, max_length=DESCRIPTION_MAX_LENGTH)
                signal.benefits = sanitize_text(raw_benefits)
                
            except (PlaywrightTimeout, PlaywrightError) as e:
                logger.warning(f"Failed to fetch details for {signal.link}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error fetching details for {signal.link}: {e}")
            finally:
                # Proper cleanup to prevent memory leaks
                if page:
                    try:
                        await page.close()
                    except Exception as e:
                        logger.debug(f"Failed to close page: {e}")
                    finally:
                        page = None


class BaseScraper:
    """Base class for all site-specific scrapers."""
    def __init__(self, engine: ScrapeEngine, site_name: str):
        self.engine = engine
        self.site_name = site_name
        self.config = CONFIG.get('scrapers', {}).get(site_name, {})
        self.extraction_stats = {'total': 0, 'success': 0, 'failed_validation': 0, 'duplicates': 0}
        # Get performance config with per-scraper overrides
        perf_config = CONFIG.get('performance', {})
        self.scroll_delay = perf_config.get('scraper_delays', {}).get(site_name, {}).get('scroll_delay', 
                                                                                          perf_config.get('scroll_delay_sec', 1.5))

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
                # Remove bullet characters and normalize whitespace
                txt = txt.lstrip('•\u2022\u2023\u25E6\u25AA\u25AB').strip()
                txt = ' '.join(txt.split())
                if txt and len(txt) > 1:
                    return sanitize_text(txt)
        return "Unknown Employer"
    
    async def extract_city(self, card):
        """Extract city from job card using configured selectors."""
        selectors = self.config.get('city_selectors', [])
        
        for sel in selectors:
            try:
                el = await card.query_selector(sel)
                if el:
                    txt = (await el.inner_text()).strip()
                    # Clean up common patterns
                    txt = txt.replace(',', '').split('-')[0].split('(')[0].strip()
                    if txt and len(txt) > 1 and len(txt) < 50:  # Reasonable city name length
                        return txt
            except Exception:
                continue
        
        # Fallback to text-based city detection using config with word boundaries
        try:
            card_text = (await card.inner_text()).lower()
            fallback_cities = CONFIG.get('common', {}).get('fallback_cities', [])
            for city in fallback_cities:
                # Use word boundaries to avoid false positives (e.g., "Praha" in "Praha Solutions")
                pattern = r'' + re.escape(city) + r''
                if re.search(pattern, card_text):
                    return city.title()
        except Exception:
            pass
        
        return "CZ"  # Default fallback


class PagedScraper(BaseScraper):
    """Handles scrapers with numbered pagination (Jobs.cz, Prace.cz, Cocuma)."""
    
    async def run(self, limit=50):
        # Check circuit breaker
        if CIRCUIT_BREAKER.is_open(self.site_name):
            logger.warning(f"Skipping {self.site_name} - circuit breaker is open")
            return
        
        context = await self.engine.get_context()
        page = await context.new_page()
        pbar = tqdm(total=limit, desc=f"[*] {self.site_name}", unit="pg")

        base_url = self.config.get('base_url')
        card_sel = self.config.get('card')
        title_sel = self.config.get('title')
        
        if not base_url or not card_sel or not title_sel:
            logger.error(f"{self.site_name}: Missing required config (base_url, card, or title)")
            await context.close()
            return

        consecutive_failures = 0  # Track consecutive failures
        
        for page_num in range(1, limit + 1):
            if shutdown_handler.is_shutdown_requested():
                logger.info(f"{self.site_name}: Shutdown requested, stopping gracefully")
                break
            
            try:
                # Use first_page_url if configured (fix for Cocuma)
                if page_num == 1 and 'first_page_url' in self.config:
                    url = self.config['first_page_url']
                else:
                    url = f"{base_url}{page_num}"
                
                await rate_limit(1.0, 2.0)  # Add rate limiting
                
                await page.goto(url, timeout=PAGE_TIMEOUT_MS)
                await page.wait_for_selector(card_sel, timeout=SELECTOR_TIMEOUT_MS)
                cards = await page.query_selector_all(card_sel)
                if not cards: break

                batch = []
                for card in cards:
                    title_el = await card.query_selector(title_sel)
                    if not title_el: continue
                    
                    company_name = await self.extract_company(card)
                    city = await self.extract_city(card)
                    
                    # Try title element first, then fallback to card itself (fix for Cocuma)
                    link = await title_el.get_attribute("href")
                    if not link:
                        link = await card.get_attribute("href")
                        
                    if not link:
                        logger.debug(f"Skipping card with no link")
                        continue
                    if not link.startswith("http"):
                        domain = self.config.get('domain', base_url.split('/prace')[0].split('/nabidky')[0].split('/jobs')[0])
                        link = domain + link
                    
                    if CORE.is_known(link):
                        self.extraction_stats['duplicates'] += 1
                        continue

                    # Salary
                    salary = None
                    sal_sel = self.config.get('salary')
                    if sal_sel:
                        sal_el = await card.query_selector(sal_sel)
                        salary = await sal_el.inner_text() if sal_el else None
                    
                    # Validate extracted data
                    self.extraction_stats['total'] += 1
                    title_text = await title_el.inner_text()
                    if not validate_job_data(title_text, company_name, link):
                        self.extraction_stats['failed_validation'] += 1
                        logger.debug(f"Skipping invalid job data: {link}")
                        continue
                    
                    sig = JobSignal(
                        title=sanitize_text(await title_el.inner_text()),
                        company=company_name,
                        link=link,
                        source=self.site_name,
                        salary=salary,
                        location=city
                    )
                    batch.append(sig)
                    self.extraction_stats['success'] += 1

                if batch:
                    await asyncio.gather(*(self.engine.scrape_detail(context, s) for s in batch))
                    for s in batch: CORE.add_signal(s)
                
                pbar.update(1)
                consecutive_failures = 0  # Reset on success
                CIRCUIT_BREAKER.record_success(self.site_name)
                
                if not batch and page_num > 5:
                    break
                    
            except (PlaywrightTimeout, PlaywrightError) as e:
                consecutive_failures += 1
                logger.warning(f"{self.site_name} page {page_num} error: {e}")
                
                # Continue instead of break, with failure threshold
                if consecutive_failures >= 3:
                    logger.error(f"{self.site_name}: {consecutive_failures} consecutive failures, stopping")
                    CIRCUIT_BREAKER.record_failure(self.site_name)
                    break
                continue  # Try next page
        
        # Log extraction metrics
        logger.info(f"{self.site_name} Extraction Metrics: "
                   f"Total={self.extraction_stats['total']}, "
                   f"Success={self.extraction_stats['success']}, "
                   f"Failed Validation={self.extraction_stats['failed_validation']}, "
                   f"Duplicates={self.extraction_stats['duplicates']}")
        
        await context.close()


class StartupJobsScraper(BaseScraper):
    async def run(self, limit=500):
        if CIRCUIT_BREAKER.is_open(self.site_name):
            logger.warning(f"Skipping {self.site_name} - circuit breaker is open")
            return
        
        context = await self.engine.get_context()
        page = await context.new_page()
        
        base_url = self.config.get('base_url')
        card_sel = self.config.get('card')
        
        if not base_url or not card_sel:
            logger.error(f"{self.site_name}: Missing required config (base_url or card)")
            await context.close()
            return
        
        try:
            await page.goto(base_url, timeout=PAGE_TIMEOUT_MS)
            
            # Handle cookie consent
            try:
                await page.get_by_text("Přijmout").click(timeout=5000)
            except Exception as e:
                logger.debug(f"Cookie consent button not found or click failed: {e}")
            
            pbar = tqdm(total=limit, desc=f"[*] {self.site_name}", unit="ads")
            last_count = 0
            stall_count = 0  # Track consecutive stalls for early exit
            
            # Wait for content to load
            try:
                await page.wait_for_selector(card_sel, timeout=SELECTOR_TIMEOUT_MS * 1.5)
            except Exception as e:
                logger.warning(f"{self.site_name}: Timed out waiting for {card_sel}: {e}")

            # Robust Infinite Scroll with Button Click and Stall Detection
            for _ in range(50):
                if shutdown_handler.is_shutdown_requested():
                    logger.info(f"{self.site_name}: Shutdown requested, stopping gracefully")
                    break 
                await page.keyboard.press("End")
                await asyncio.sleep(self.scroll_delay * 1.3)
                
                # Try to click "Load more" button if it exists
                try:
                    load_more = page.locator("button:has-text('Načíst další'), button:has-text('Zobrazit více'), a.more-jobs")
                    if await load_more.count() > 0 and await load_more.first.is_visible():
                        await load_more.first.click(force=True)
                        await asyncio.sleep(self.scroll_delay * 1.3)
                except Exception as e:
                    logger.debug(f"Load more button click failed: {e}")
                
                cards = await page.query_selector_all(card_sel)
                
                if len(cards) >= limit:
                    break
                
                if len(cards) == last_count:
                    stall_count += 1
                    if stall_count >= STALL_THRESHOLD:
                        logger.debug(f"{self.site_name}: Scroll stalled after {len(cards)} cards, exiting early")
                        break
                    # If stuck, try scrolling up and down
                    await page.mouse.wheel(0, -500)
                    await asyncio.sleep(0.5)
                    await page.mouse.wheel(0, 500)
                    await asyncio.sleep(1)
                else:
                    stall_count = 0  # Reset on progress
                
                new_cards = len(cards) - last_count
                if new_cards > 0:
                    pbar.update(min(new_cards, limit - pbar.n))
                last_count = len(cards)
            
            cards = await page.query_selector_all(card_sel)
            batch = []
            for card in cards[:limit]:
                try:
                    href = await card.get_attribute("href")
                    if not href:
                        continue
                    
                    if href.startswith("http"):
                        link = href
                    else:
                        domain = self.config.get('domain', 'https://www.startupjobs.cz')
                        link = domain + href

                    if CORE.is_known(link):
                        continue
                    
                    company_name = await self.extract_company(card)
                    city = await self.extract_city(card)

                    salary = None
                    # StartupJobs specific salary extraction attempt (using compiled regex)
                    txt = await card.inner_text()
                    match = SALARY_PATTERN.search(txt)
                    if match:
                        salary = match.group(0)

                    title_sel = self.config.get('title', 'h2')
                    title_el = await card.query_selector(title_sel)
                    if title_el:
                        title = (await title_el.inner_text()).split('\n')[0]
                    else:
                        title = (await card.inner_text()).split("\n")[0]

                    sig = JobSignal(
                        title=sanitize_text(title),
                        company=company_name,
                        link=link,
                        source=self.site_name,
                        salary=salary,
                        location=city
                    )
                    batch.append(sig)
                    self.extraction_stats['success'] += 1
                except Exception as e:
                    logger.debug(f"Failed to process StartupJobs card: {e}")
                    continue
            
            if batch:
                await asyncio.gather(*(self.engine.scrape_detail(context, s) for s in batch))
                for s in batch:
                    CORE.add_signal(s)
            
            CIRCUIT_BREAKER.record_success(self.site_name)
                
        except Exception as e:
            logger.error(f"StartupJobs failed: {e}")
            CIRCUIT_BREAKER.record_failure(self.site_name)
        finally:
            await context.close()


class WttjScraper(BaseScraper):
    async def run(self, limit=200):
        if CIRCUIT_BREAKER.is_open(self.site_name):
            logger.warning(f"Skipping {self.site_name} - circuit breaker is open")
            return
        
        context = await self.engine.get_context()
        page = await context.new_page()
        
        base_url = self.config.get('base_url')
        card_sel = self.config.get('card')
        link_sel = self.config.get('link')
        title_sel = self.config.get('title')
        
        if not base_url or not card_sel or not link_sel:
            logger.error(f"{self.site_name}: Missing required config")
            await context.close()
            return
        
        try:
            # WTTJ is heavy, wait for commit first then load
            try:
                await page.goto(base_url, timeout=PAGE_TIMEOUT_MS, wait_until="commit")
                await page.wait_for_selector(card_sel, timeout=SELECTOR_TIMEOUT_MS * 2)
            except Exception as e:
                logger.warning(f"WTTJ failed initial load: {e}")
                return

            pbar = tqdm(total=limit, desc=f"[*] {self.site_name}", unit="ads")
            last_count = 0
            stall_count = 0
            
            # Scroll loop with stall detection
            for _ in range(40):
                if shutdown_handler.is_shutdown_requested():
                    logger.info(f"{self.site_name}: Shutdown requested, stopping gracefully")
                    break 
                
                # Use JS scroll as End key might be flaky on some sites
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(self.scroll_delay)
                
                cards = await page.query_selector_all(card_sel)
                if len(cards) >= limit:
                    break
                    
                if len(cards) == last_count:
                    stall_count += 1
                    if stall_count >= STALL_THRESHOLD:
                        logger.debug(f"WTTJ: Scroll stalled after {len(cards)} cards")
                        break
                else:
                    stall_count = 0
                last_count = len(cards)
            
            cards = await page.query_selector_all(card_sel)
            batch = []
            for card in cards[:limit]:
                try:
                    link_el = await card.query_selector(link_sel)
                    if not link_el:
                        continue
                    
                    domain = self.config.get('domain', 'https://www.welcometothejungle.com')
                    href = await link_el.get_attribute("href")
                    if not href:
                        continue
                    link = domain + href if not href.startswith("http") else href
                    
                    if CORE.is_known(link):
                        continue
                    
                    company_name = await self.extract_company(card)
                    city = await self.extract_city(card)
                    
                    title_el = await card.query_selector(title_sel) if title_sel else None
                    title = await title_el.inner_text() if title_el else "Unknown Role"

                    sig = JobSignal(
                        title=sanitize_text(title),
                        company=company_name,
                        link=link,
                        source=self.site_name,
                        location=city
                    )
                    batch.append(sig)
                    self.extraction_stats['success'] += 1
                    pbar.update(1)
                except Exception as e:
                    logger.debug(f"Failed to process WTTJ card: {e}")
                    continue
            
            if batch:
                await asyncio.gather(*(self.engine.scrape_detail(context, s) for s in batch))
                for s in batch:
                    CORE.add_signal(s)
            
            CIRCUIT_BREAKER.record_success(self.site_name)
            
        except Exception as e:
            logger.warning(f"WTTJ scraping failed: {e}")
            CIRCUIT_BREAKER.record_failure(self.site_name)
        finally:
            await context.close()


class LinkedinScraper(BaseScraper):
    async def run(self, limit=100):
        if CIRCUIT_BREAKER.is_open(self.site_name):
            logger.warning(f"Skipping {self.site_name} - circuit breaker is open")
            return
        
        context = await self.engine.get_context()
        page = await context.new_page()
        
        base_url = self.config.get('base_url')
        card_sel = self.config.get('card')
        link_sel = self.config.get('link')
        title_sel = self.config.get('title')
        
        if not base_url or not card_sel or not link_sel or not title_sel:
            logger.error(f"{self.site_name}: Missing required config")
            await context.close()
            return
        
        try:
            await page.goto(base_url, timeout=PAGE_TIMEOUT_MS)
            pbar = tqdm(total=limit, desc=f"[*] {self.site_name}", unit="ads")
            
            last_count = 0
            stall_count = 0
            
            # Scroll loop with stall detection
            for _ in range(50):
                if shutdown_handler.is_shutdown_requested():
                    logger.info(f"{self.site_name}: Shutdown requested, stopping gracefully")
                    break
                
                # Try clicking "See more jobs" if present
                try:
                    btn = page.locator("button.infinite-scroller__show-more-button")
                    if await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(2)
                except Exception:
                    pass

                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(self.scroll_delay)
                
                cards = await page.query_selector_all(card_sel)
                if len(cards) >= limit:
                    break
                    
                if len(cards) == last_count:
                    stall_count += 1
                    if stall_count >= STALL_THRESHOLD:
                        logger.debug(f"LinkedIn: Scroll stalled after {len(cards)} cards")
                        break
                else:
                    stall_count = 0
                last_count = len(cards)
            
            cards = await page.query_selector_all(card_sel)
            batch = []  # Collect signals first, then fetch details
            
            for card in cards[:limit]:
                try:
                    link_el = await card.query_selector(link_sel)
                    if not link_el:
                        continue
                    href = await link_el.get_attribute("href")
                    if not href:
                        continue
                    link = href.split('?')[0]
                    if CORE.is_known(link):
                        continue
                    
                    company_name = await self.extract_company(card)
                    city = await self.extract_city(card)
                    
                    title_el = await card.query_selector(title_sel)
                    title = await title_el.inner_text() if title_el else "Unknown Role"
                    
                    sig = JobSignal(
                        title=sanitize_text(title),
                        company=company_name,
                        link=link,
                        source=self.site_name,
                        location=city
                    )
                    batch.append(sig)
                    self.extraction_stats['success'] += 1
                    pbar.update(1)
                except Exception as e:
                    logger.debug(f"Failed to process LinkedIn card: {e}")
                    continue
            
            # Actually fetch details for LinkedIn jobs
            if batch:
                logger.info(f"Fetching details for {len(batch)} LinkedIn jobs")
                await asyncio.gather(*(self.engine.scrape_detail(context, s) for s in batch))
                for s in batch:
                    CORE.add_signal(s)
            
            CIRCUIT_BREAKER.record_success(self.site_name)
            
        except Exception as e:
            logger.warning(f"LinkedIn scraping failed: {e}")
            CIRCUIT_BREAKER.record_failure(self.site_name)
        finally:
            await context.close()


async def main():
    logger.info("=== OMNISCRAPE v18.0: Enhanced Security & Reliability ===")
    
    # Register cleanup callbacks
    shutdown_handler.register_cleanup(lambda: logger.info("Cleanup: Saving progress..."))

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        engine = ScrapeEngine(browser)
        
        # Initialize scrapers
        jobs_cz = PagedScraper(engine, "Jobs.cz")
        prace_cz = PagedScraper(engine, "Prace.cz")
        cocuma = PagedScraper(engine, "Cocuma") 
        startup = StartupJobsScraper(engine, "StartupJobs")
        wttj = WttjScraper(engine, "WTTJ")
        linkedin = LinkedinScraper(engine, "LinkedIn")
        
        try:
            await asyncio.gather(
                jobs_cz.run(limit=75),     # 75 pages * 20 ads = 1500 (PRIMARY SOURCE)
                prace_cz.run(limit=75),    # 75 pages * 20 ads = 1500 (PRIMARY SOURCE)
                startup.run(limit=300),    # 300 job ads
                wttj.run(limit=200),       # 200 job ads (often fails)
                cocuma.run(limit=10),      # 10 pages (often 0 results)
                linkedin.run(limit=300)    # 300 job ads
            )
        except KeyboardInterrupt:
            logger.warning("Received interrupt signal, initiating graceful shutdown...")
            shutdown_handler.request_shutdown()
        finally:
            await browser.close()
            await shutdown_handler.cleanup()
    
    CORE.cleanup_expired(threshold_minutes=180)
    logger.info("=== SCRAPING COMPLETE ===")

if __name__ == "__main__":
    CORE.reanalyze_all()
    asyncio.run(main())
