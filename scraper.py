import asyncio
import re
import logging
import yaml
import os
from typing import List, Optional, Dict

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout, Error as PlaywrightError
from playwright_stealth import Stealth
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
    shutdown_handler,
    Heartbeat
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
CONCURRENCY = 5
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

# --- GLOBAL INSTANCES (Initialized in main) ---
CORE = None
CIRCUIT_BREAKER = None

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.FileHandler("scraper.log"), logging.StreamHandler()]
)
logger = logging.getLogger("OmniScrape")

class ScrapeEngine:
    """The heavy-duty engine that handles browser lifecycle and concurrency."""

    def __init__(self, browser):
        self.browser = browser
        self.semaphore = asyncio.Semaphore(CONCURRENCY)
        self.common_config = CONFIG.get('common', {})

    async def get_context(self, proxy_server: Optional[str] = None):
        proxy = {"server": proxy_server} if proxy_server else None
        
        context = await self.browser.new_context(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            user_agent=get_random_user_agent(),
            proxy=proxy
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
                await Stealth().apply_stealth_async(page)
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

                # Robust extraction with retries for "Execution context destroyed"
                raw_description = ""
                raw_benefits = ""
                
                for attempt in range(3):
                    try:
                        # Extraction logic with null safety
                        raw_description = await page.evaluate("""() => {
                            const s = ['div.JobDescription', 'article', 'main', '.jd-content', '.job-detail__description'];
                            for (let x of s) {
                                let el = document.querySelector(x);
                                if (el && el.innerText) return el.innerText;
                            }
                            return document.body?.innerText || '';
                        }""")

                        raw_benefits = await page.evaluate("""() => {
                            const tags = Array.from(document.querySelectorAll('.benefit-item, .Tag--success, .Badge--success, [data-test*="benefit"]'));
                            return tags.map(t => t.innerText?.trim() || '').filter(t => t.length > 1).join(', ');
                        }""")
                        break # Success
                    except PlaywrightError as e:
                        if "Execution context was destroyed" in str(e) and attempt < 2:
                            logger.debug(f"Context destroyed, retrying extraction (attempt {attempt+1})...")
                            await asyncio.sleep(1.0)
                            continue
                        raise e

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
                txt = re.sub(r'^[••‣◦▪▫\s]+', '', txt).strip()
                txt = ' '.join(txt.split())
                if txt and len(txt) > 1:
                    return sanitize_text(txt)
            else:
                logger.debug(f"{self.site_name}: Company selector '{sel}' returned no element")
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
                else:
                    logger.debug(f"{self.site_name}: City selector '{sel}' returned no element")
            except Exception as e:
                logger.debug(f"{self.site_name}: City extraction error for selector '{sel}': {e}")
                continue
        
        # Fallback to text-based city detection using config with word boundaries
        try:
            card_text = (await card.inner_text()).lower()
            fallback_cities = CONFIG.get('common', {}).get('fallback_cities', [])
            for city in fallback_cities:
                # Use word boundaries to avoid false positives (e.g., "Praha" in "Praha Solutions")
                pattern = r'\b' + re.escape(city.lower()) + r'\b'
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
        await Stealth().apply_stealth_async(page)  # Apply stealth to listing page
        pbar = tqdm(total=limit, desc=f"[*] {self.site_name}", unit="pg")

        base_url = self.config.get('base_url')
        card_sel = self.config.get('card')
        title_sel = self.config.get('title')
        
        if not base_url or not card_sel or not title_sel:
            logger.error(f"{self.site_name}: Missing required config (base_url, card, or title)")
            await context.close()
            return

        consecutive_failures = 0  # Track consecutive failures
        
        try:
            for page_num in range(1, limit + 1):
                if shutdown_handler.is_shutdown_requested():
                    logger.info(f"{self.site_name}: Shutdown requested, stopping gracefully")
                    break
                
                # Context Rotation: Create fresh browser fingerprint every 10 pages
                if page_num > 1 and page_num % 10 == 1:
                    logger.info(f"{self.site_name}: Rotating browser context (page {page_num})")
                    await context.close()
                    context = await self.engine.get_context()
                    page = await context.new_page()
                    await Stealth().apply_stealth_async(page)
                
                # Rate Limit Cooldown: 5-minute pause every 20 pages for rate-limited sites
                # This avoids server-side IP blocking without needing residential proxies
                if page_num > 1 and page_num % 20 == 1 and self.site_name in ['Jobs.cz', 'Prace.cz']:
                    cooldown_minutes = 5
                    logger.info(f"{self.site_name}: Rate limit cooldown - waiting {cooldown_minutes} minutes (page {page_num})...")
                    await asyncio.sleep(cooldown_minutes * 60)
                    # Rotate context after cooldown for fresh fingerprint
                    await context.close()
                    context = await self.engine.get_context()
                    page = await context.new_page()
                    await Stealth().apply_stealth_async(page)
                    logger.info(f"{self.site_name}: Cooldown complete, resuming scrape")

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
        finally:
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
        await Stealth().apply_stealth_async(page)
        
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

            # FIX: Button-based pagination - click "Načíst další stránku" repeatedly
            # StartupJobs has 2 elements per job (mobile/desktop), so we need 2x cards
            target_cards = limit * 2  # Account for duplicates
            click_count = 0
            max_clicks = 50  # Safety limit
            seen_links = set()
            total_saved = 0
            
            while click_count < max_clicks and total_saved < limit:
                if shutdown_handler.is_shutdown_requested():
                    logger.info(f"{self.site_name}: Shutdown requested, stopping gracefully")
                    break
                
                # Check current card count and process batch if enough new ones found
                cards = await page.query_selector_all(card_sel)
                current_count = len(cards)
                
                # Incremental processing every 5 clicks or when we reach target
                if click_count > 0 and (click_count % 5 == 0 or current_count >= target_cards):
                    new_batch = []
                    for card in cards:
                        try:
                            href = await card.get_attribute("href")
                            if not href: continue
                            link = href if href.startswith("http") else f"{self.config.get('domain', 'https://www.startupjobs.cz')}{href}"
                            
                            if link in seen_links: continue
                            seen_links.add(link)
                            
                            if CORE.is_known(link):
                                self.extraction_stats['duplicates'] = self.extraction_stats.get('duplicates', 0) + 1
                                continue
                            
                            company_name = await self.extract_company(card)
                            city = await self.extract_city(card)
                            
                            txt = await card.inner_text()
                            match = SALARY_PATTERN.search(txt)
                            salary = match.group(0) if match else None
                            
                            title_sel = self.config.get('title', 'h2')
                            title_el = await card.query_selector(title_sel)
                            title = (await title_el.inner_text()).split('\n')[0] if title_el else txt.split('\n')[0]
                            
                            sig = JobSignal(
                                title=sanitize_text(title),
                                company=company_name,
                                link=link,
                                source=self.site_name,
                                salary=salary,
                                location=city
                            )
                            new_batch.append(sig)
                        except Exception as e:
                            logger.error(f"StartupJobs: Error processing card: {e}")
                            continue

                    if new_batch:
                        logger.info(f"StartupJobs: Processing incremental batch of {len(new_batch)} jobs...")
                        await asyncio.gather(*(self.engine.scrape_detail(context, s) for s in new_batch))
                        for s in new_batch: CORE.add_signal(s)
                        total_saved += len(new_batch)
                        self.extraction_stats['success'] = self.extraction_stats.get('success', 0) + len(new_batch)
                        pbar.update(len(new_batch))

                # Check if we have enough
                if current_count >= target_cards or total_saved >= limit:
                    break
                
                # Scroll to bottom and look for button
                await page.keyboard.press("End")
                await asyncio.sleep(1.5)
                
                # Try to find and click the button using JavaScript
                try:
                    clicked = await page.evaluate("""() => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const loadMore = buttons.find(b => b.innerText.includes('Načíst další stránku'));
                        if (loadMore) {
                            loadMore.scrollIntoView();
                            loadMore.click();
                            return true;
                        }
                        return false;
                    }""")
                    
                    if clicked:
                        click_count += 1
                        logger.debug(f"StartupJobs: JS button click #{click_count}")
                        await asyncio.sleep(3)
                    else:
                        break
                except Exception as e:
                    logger.debug(f"StartupJobs: JS button click failed: {e}")
                    break
            
            # Final batch for any remaining cards
            cards = await page.query_selector_all(card_sel)
            final_batch = []
            for card in cards:
                try:
                    href = await card.get_attribute("href")
                    if not href: continue
                    link = href if href.startswith("http") else f"{self.config.get('domain', 'https://www.startupjobs.cz')}{href}"
                    
                    if link in seen_links: continue
                    seen_links.add(link)
                    
                    if CORE.is_known(link): continue
                    
                    company_name = await self.extract_company(card)
                    city = await self.extract_city(card)
                    txt = await card.inner_text()
                    match = SALARY_PATTERN.search(txt)
                    salary = match.group(0) if match else None
                    title_sel = self.config.get('title', 'h2')
                    title_el = await card.query_selector(title_sel)
                    title = (await title_el.inner_text()).split('\n')[0] if title_el else txt.split('\n')[0]
                    
                    final_batch.append(JobSignal(
                        title=sanitize_text(title),
                        company=company_name,
                        link=link,
                        source=self.site_name,
                        salary=salary,
                        location=city
                    ))
                except Exception: continue
            
            if final_batch:
                logger.info(f"StartupJobs: Processing final batch of {len(final_batch)} jobs...")
                await asyncio.gather(*(self.engine.scrape_detail(context, s) for s in final_batch))
                for s in final_batch: CORE.add_signal(s)
                self.extraction_stats['success'] = self.extraction_stats.get('success', 0) + len(final_batch)
                pbar.update(len(final_batch))
            
            CIRCUIT_BREAKER.record_success(self.site_name)
            logger.info(f"StartupJobs completed: total success count {self.extraction_stats.get('success', 0)}")
                
        except Exception as e:
            logger.error(f"StartupJobs failed: {e}")
            CIRCUIT_BREAKER.record_failure(self.site_name)
        finally:
            await context.close()


class WttjScraper(BaseScraper):
    """WTTJ uses URL-based pagination (?page=N), not infinite scroll."""
    
    async def run(self, limit=200):
        if CIRCUIT_BREAKER.is_open(self.site_name):
            logger.warning(f"Skipping {self.site_name} - circuit breaker is open")
            return
        
        context = await self.engine.get_context()
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        # WTTJ base URL without page parameter
        base_url = self.config.get('base_url')  # https://www.welcometothejungle.com/cs/jobs?aroundQuery=Czechia
        card_sel = self.config.get('card')
        link_sel = self.config.get('link')
        title_sel = self.config.get('title')
        
        if not base_url or not card_sel or not link_sel:
            logger.error(f"{self.site_name}: Missing required config")
            await context.close()
            return
        
        pbar = tqdm(total=limit, desc=f"[*] {self.site_name}", unit="ads")
        total_collected = 0
        consecutive_empty = 0
        seen_links = set()  # Track unique links to avoid duplicates
        
        try:
            # FIX: Use URL pagination instead of scroll
            # WTTJ has ~30 jobs per page, iterate through pages
            for page_num in range(1, 25):  # Max 25 pages (~750 jobs)
                if shutdown_handler.is_shutdown_requested():
                    logger.info(f"{self.site_name}: Shutdown requested, stopping gracefully")
                    break
                
                if total_collected >= limit:
                    break
                
                # Construct paginated URL
                page_url = f"{base_url}&page={page_num}"
                
                try:
                    await rate_limit(1.0, 2.0)  # Rate limiting between pages
                    await page.goto(page_url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
                    await page.wait_for_selector(card_sel, timeout=SELECTOR_TIMEOUT_MS * 2)
                except Exception as e:
                    logger.warning(f"WTTJ page {page_num} failed to load: {e}")
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        logger.debug(f"WTTJ: 3 consecutive failures, stopping")
                        break
                    continue
                
                cards = await page.query_selector_all(card_sel)
                if not cards:
                    consecutive_empty += 1
                    if consecutive_empty >= 2:
                        logger.debug(f"WTTJ: No cards found on page {page_num}, stopping")
                        break
                    continue
                
                consecutive_empty = 0  # Reset on success
                batch = []
                
                for card in cards:
                    if total_collected >= limit:
                        break
                    
                    try:
                        link_el = await card.query_selector(link_sel)
                        if not link_el:
                            continue
                        
                        domain = self.config.get('domain', 'https://www.welcometothejungle.com')
                        href = await link_el.get_attribute("href")
                        if not href:
                            continue
                        link = domain + href if not href.startswith("http") else href
                        
                        # Deduplicate (WTTJ has 2 elements per card: mobile/desktop)
                        if link in seen_links:
                            continue
                        seen_links.add(link)
                        
                        if CORE.is_known(link):
                            self.extraction_stats['duplicates'] = self.extraction_stats.get('duplicates', 0) + 1
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
                        total_collected += 1
                        pbar.update(1)
                    except Exception as e:
                        logger.debug(f"Failed to process WTTJ card: {e}")
                        continue
                
                if batch:
                    await asyncio.gather(*(self.engine.scrape_detail(context, s) for s in batch))
                    for s in batch:
                        CORE.add_signal(s)
                
                logger.debug(f"WTTJ page {page_num}: collected {len(batch)} jobs (total: {total_collected})")
            
            CIRCUIT_BREAKER.record_success(self.site_name)
            logger.info(f"WTTJ completed: {total_collected} jobs collected")
            
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
        
        proxy = os.environ.get("LINKEDIN_PROXY")
        if proxy:
            logger.info("Using proxy for LinkedIn")
        else:
            logger.warning("LinkedIn: No LINKEDIN_PROXY env var set. LinkedIn blocks headless browsers without residential proxies. Set: $env:LINKEDIN_PROXY='http://user:pass@proxy:port'")
        
        context = await self.engine.get_context(proxy_server=proxy)
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
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
    
    global CORE, CIRCUIT_BREAKER
    CORE = IntelligenceCore()
    CIRCUIT_BREAKER = CircuitBreaker(failure_threshold=5, timeout_seconds=300)
    
    # Setup graceful shutdown
    shutdown_handler.setup_signal_handlers()
    
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
        # LinkedIn removed: blocks headless browsers without residential proxy

        try:
            # Batch 1: High-volume standard boards (Concurrent)
            logger.info("Batch 1: Standard Job Boards")
            with Heartbeat(interval=30.0, message="Scraping Batch 1: Jobs.cz, Prace.cz..."):
                await asyncio.gather(
                    jobs_cz.run(limit=100),
                    prace_cz.run(limit=50)
                )

            # Batch 2: Tech-focused & sensitive sites (Sequential for reliability)
            logger.info("Batch 2: Tech-focused Sites")
            with Heartbeat(interval=30.0, message="Scraping Batch 2: StartupJobs..."):
                await startup.run(limit=600)
            with Heartbeat(interval=30.0, message="Scraping Batch 2: WTTJ..."):
                await wttj.run(limit=600)

            # Batch 3: Niche / Others
            logger.info("Batch 3: Niche Channels")
            with Heartbeat(interval=30.0, message="Scraping Batch 3: Cocuma..."):
                await cocuma.run(limit=30)
            
        except KeyboardInterrupt:
            logger.warning("Received interrupt signal, initiating graceful shutdown...")
            shutdown_handler.request_shutdown()
        finally:
            await browser.close()
            await shutdown_handler.cleanup()

    # Enhanced cleanup strategy for GitHub weekly runs
    # Remove jobs not seen in last 14 days (2 scrape cycles for safety)
    CORE.cleanup_expired(threshold_minutes=14 * 24 * 60)  # 14 days

    # Compact database to reclaim space from deleted records
    CORE.vacuum_database()

    # Log final database statistics
    stats = CORE.get_database_stats()
    logger.info(f"=== DATABASE STATISTICS ===")
    logger.info(f"Total active jobs: {stats['total_jobs']}")
    logger.info(f"Database size: {stats['db_size_mb']:.2f} MB")
    logger.info(f"Jobs by source: {stats['by_source']}")
    logger.info(f"Oldest job: {stats['oldest_job']}")
    logger.info(f"Newest job: {stats['newest_job']}")
    logger.info("=== SCRAPING COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())

