import asyncio
import time
import random
import re
from playwright.async_api import async_playwright
from playwright_stealth import stealth
import analyzer
from tqdm.asyncio import tqdm

# --- CORE ARCHITECTURE ---
CORE = analyzer.IntelligenceCore()
CONCURRENCY = 5

async def intercept_noise(route):
    """Blocks heavy media and trackers."""
    bad_patterns = ["google-analytics", "hotjar", "facebook", "pixel", "doubleclick"]
    if route.request.resource_type in ["image", "media", "font"]:
        await route.abort()
    elif any(p in route.request.url for p in bad_patterns):
        await route.abort()
    else:
        await route.continue_()

async def get_stealth_context(browser):
    return await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

async def scrape_detail(context, url, semaphore):
    """Deep extraction with stealth and error resilience."""
    if not url or "linkedin.com" in url: return ""
    async with semaphore:
        page = await context.new_page()
        try:
            # Explicit function call check
            if callable(stealth):
                await stealth(page)
            await page.route("**/*", intercept_noise)
            # Human jitter
            await asyncio.sleep(random.uniform(0.5, 1.2))
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            content = await page.evaluate("""() => {
                const s = ['div.JobDescription', 'article', 'main', '.jd-content', '.job-detail__description', '.job-body'];
                for (let x of s) { let el = document.querySelector(x); if (el) return el.innerText; }
                return document.body.innerText;
            }""")
            await page.close()
            return content.strip()[:5000]
        except:
            await page.close()
            return ""

# --- SITE ENGINES ---

async def scrape_standard(browser, name, base_url, card_sel, title_sel, limit=100):
    """Engine for Jobs.cz and Prace.cz."""
    context = await get_stealth_context(browser)
    page = await context.new_page()
    if callable(stealth):
        await stealth(page)
    await page.route("**/*", intercept_noise)
    semaphore = asyncio.Semaphore(CONCURRENCY)
    pbar = tqdm(total=limit, desc=f"[*] {name}", unit="pg")
    
    for page_num in range(1, limit + 1):
        try:
            url = f"{base_url}{page_num}"
            await page.goto(url, timeout=60000)
            await page.wait_for_selector(card_sel, timeout=10000)
            cards = await page.query_selector_all(card_sel)
            if not cards: break
            
            batch_tasks = []
            metadata_list = []
            for card in cards:
                title_el = await card.query_selector(title_sel)
                if not title_el: continue
                link = await title_el.get_attribute("href")
                if not link.startswith("http"):
                    link = ("https://www.jobs.cz" if "jobs" in base_url else "https://www.prace.cz") + link
                
                if CORE.is_known(link): continue
                
                metadata_list.append({
                    "title": await title_el.inner_text(),
                    "company": "Market Signal", 
                    "link": link, "source": name, "salary": None
                })
                batch_tasks.append(scrape_detail(context, link, semaphore))
            
            if batch_tasks:
                desc_results = await asyncio.gather(*batch_tasks)
                for i, desc in enumerate(desc_results):
                    metadata_list[i]['description'] = desc
                    CORE.add_signal(metadata_list[i])
            pbar.update(1)
            if not batch_tasks and page_num > 5: break
        except: break
    await context.close()

async def scrape_startupjobs(browser, limit=1000):
    name = "StartupJobs"
    context = await get_stealth_context(browser)
    page = await context.new_page()
    if callable(stealth):
        await stealth(page)
    await page.goto("https://www.startupjobs.cz/nabidky")
    try: await page.get_by_text("Přijmout").click(timeout=5000)
    except: pass
    
    semaphore = asyncio.Semaphore(CONCURRENCY)
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
    metadata_list = []
    batch_tasks = []
    for card in cards[:limit]:
        link = "https://www.startupjobs.cz" + await card.get_attribute("href")
        if CORE.is_known(link): continue
        metadata_list.append({
            "title": (await card.inner_text()).split("\n")[0],
            "company": "Startup", "link": link, "source": name, "salary": None
        })
        batch_tasks.append(scrape_detail(context, link, semaphore))
    
    if batch_tasks:
        desc_results = await asyncio.gather(*batch_tasks)
        for i, desc in enumerate(desc_results):
            metadata_list[i]['description'] = desc
            CORE.add_signal(metadata_list[i])
    await context.close()

async def scrape_wttj(browser, limit=500):
    name = "WTTJ"
    context = await get_stealth_context(browser)
    page = await context.new_page()
    if callable(stealth):
        await stealth(page)
    await page.goto("https://www.welcometothejungle.com/cs/jobs?aroundQuery=Czechia")
    semaphore = asyncio.Semaphore(CONCURRENCY)
    pbar = tqdm(total=limit, desc=f"[*] {name}", unit="ads")
    
    for _ in range(50): 
        await page.keyboard.press("PageDown")
        await asyncio.sleep(1)
    
    cards = await page.query_selector_all("li.ais-Hits-item")
    metadata_list = []
    batch_tasks = []
    for card in cards[:limit]:
        try:
            link_el = await card.query_selector("a")
            link = "https://www.welcometothejungle.com" + await link_el.get_attribute("href")
            if CORE.is_known(link): continue
            metadata_list.append({
                "title": await (await card.query_selector("h4")).inner_text(),
                "company": "WTTJ Partner", "link": link, "source": name, "salary": None
            })
            batch_tasks.append(scrape_detail(context, link, semaphore))
            pbar.update(1)
        except: continue
    
    if batch_tasks:
        desc_results = await asyncio.gather(*batch_tasks)
        for i, desc in enumerate(desc_results):
            metadata_list[i]['description'] = desc
            CORE.add_signal(metadata_list[i])
    await context.close()

async def scrape_cocuma(browser, limit=100):
    name = "Cocuma"
    base_url = "https://www.cocuma.cz/jobs/?page="
    context = await get_stealth_context(browser)
    page = await context.new_page()
    if callable(stealth):
        await stealth(page)
    semaphore = asyncio.Semaphore(CONCURRENCY)
    pbar = tqdm(total=limit, desc=f"[*] {name}", unit="pg")
    
    for page_num in range(1, limit + 1):
        try:
            await page.goto(f"{base_url}{page_num}/")
            cards = await page.query_selector_all("a.job-thumbnail")
            if not cards: break
            
            metadata_list = []
            batch_tasks = []
            for card in cards:
                link = "https://www.cocuma.cz" + await card.get_attribute("href")
                if CORE.is_known(link): continue
                
                title_el = await card.query_selector(".job-thumbnail-title")
                comp_el = await card.query_selector(".job-thumbnail-company")
                metadata_list.append({
                    "title": await title_el.inner_text(),
                    "company": await comp_el.inner_text(),
                    "link": link, "source": name, "salary": None
                })
                batch_tasks.append(scrape_detail(context, link, semaphore))
            
            if batch_tasks:
                desc_results = await asyncio.gather(*batch_tasks)
                for i, desc in enumerate(desc_results):
                    metadata_list[i]['description'] = desc
                    CORE.add_signal(metadata_list[i])
            pbar.update(1)
        except: break
    await context.close()

async def scrape_linkedin(browser, limit=200):
    name = "LinkedIn"
    context = await get_stealth_context(browser)
    page = await context.new_page()
    if callable(stealth):
        await stealth(page)
    await page.goto("https://www.linkedin.com/jobs/search?keywords=&location=Czechia")
    pbar = tqdm(total=limit, desc=f"[*] {name}", unit="ads")
    for _ in range(20):
        await page.keyboard.press("End")
        await asyncio.sleep(2)
    cards = await page.query_selector_all("div.base-card")
    for card in cards[:limit]:
        try:
            link = (await (await card.query_selector("a")).get_attribute("href")).split('?')[0]
            if CORE.is_known(link): continue
            CORE.add_signal({
                "title": await (await card.query_selector("h3")).inner_text(),
                "company": await (await card.query_selector("h4")).inner_text(),
                "link": link, "source": name, "description": "LinkedIn Market Signal", "salary": None
            })
            pbar.update(1)
        except: continue
    await context.close()

async def main():
    print("\n--- OMNISCRAPE 2026: THE INFINITE VACUUM ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        await asyncio.gather(
            scrape_standard(browser, "Jobs.cz", "https://www.jobs.cz/prace/?page=", "article.SearchResultCard", "h2.SearchResultCard__title > a"),
            scrape_standard(browser, "Prace.cz", "https://www.prace.cz/nabidky/?page=", "li.search-result__advert", "a.link"),
            scrape_startupjobs(browser),
            scrape_wttj(browser),
            scrape_cocuma(browser),
            scrape_linkedin(browser)
        )
        await browser.close()
    print("\n--- INTEL CORE UPDATED ---")

if __name__ == "__main__":
    asyncio.run(main())