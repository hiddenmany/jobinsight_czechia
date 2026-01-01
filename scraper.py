import asyncio
import time
import random
import re
from playwright.async_api import async_playwright
from playwright_stealth import stealth
import analyzer
from analyzer import JobSignal # Explicit import for type hints
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
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )


async def scrape_detail(context, url, semaphore):
    """Deep extraction with Read-More clicker and Benefit Tagging."""
    if not url or "linkedin.com" in url:
        return "", ""
    async with semaphore:
        page = await context.new_page()
        try:
            # Check if stealth is callable
            if callable(stealth):
                await stealth(page)
            await page.route("**/*", intercept_noise)
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")

            # --- 1. Expand "Read More" Walls ---
            expand_selectors = [
                "button:has-text('Zobrazit více')",
                "button:has-text('Číst dál')",
                ".job-detail__description-button",
                "text=Read more",
            ]
            for sel in expand_selectors:
                try:
                    btn = page.locator(sel)
                    if await btn.is_visible():
                        await btn.click(force=True)
                        await asyncio.sleep(0.5)
                except:
                    pass

            # --- 2. Extract Full Content ---
            description = await page.evaluate(
                """() => {
                const s = ['div.JobDescription', 'article', 'main', '.jd-content', '.job-detail__description'];
                for (let x of s) { let el = document.querySelector(x); if (el) return el.innerText; }
                return document.body.innerText;
            }"""
            )

            # --- 3. Extract Benefit Tags ---
            benefits = await page.evaluate(
                """() => {
                const tags = Array.from(document.querySelectorAll('.benefit-item, .Tag--success, .Badge--success, [data-test*="benefit"]'));
                return tags.map(t => t.innerText.trim()).filter(t => t.length > 1).join(', ');
            }"""
            )

            await page.close()
            return description.strip()[:5000], benefits
        except:
            await page.close()
            return "", ""


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
            if not cards:
                break

            batch_tasks = []
            signals_list = [] # Renamed for clarity
            for card in cards:
                title_el = await card.query_selector(title_sel)
                if not title_el:
                    continue
                link = await title_el.get_attribute("href")
                if not link.startswith("http"):
                    link = (
                        "https://www.jobs.cz"
                        if "jobs" in base_url
                        else "https://www.prace.cz"
                    ) + link

                if CORE.is_known(link):
                    continue

                # Pre-extract salary if available in list view
                sal_el = await card.query_selector(
                    "span.Tag--success, .search-result__advert__box__item--salary"
                )
                sal_raw = await sal_el.inner_text() if sal_el else None

                # Create Typesafe Object
                sig = JobSignal(
                    title=await title_el.inner_text(),
                    company="Market Signal",
                    link=link,
                    source=name,
                    salary=sal_raw
                )
                signals_list.append(sig)
                batch_tasks.append(scrape_detail(context, link, semaphore))

            if batch_tasks:
                results = await asyncio.gather(*batch_tasks)
                for i, (desc, bens) in enumerate(results):
                    signals_list[i].description = desc
                    signals_list[i].benefits = bens
                    CORE.add_signal(signals_list[i])
            pbar.update(1)
            if not batch_tasks and page_num > 5:
                break
        except:
            break
    await context.close()


async def scrape_startupjobs(browser, limit=1000):
    name = "StartupJobs"
    context = await get_stealth_context(browser)
    page = await context.new_page()
    if callable(stealth):
        await stealth(page)
    await page.goto("https://www.startupjobs.cz/nabidky")
    try:
        await page.get_by_text("Přijmout").click(timeout=5000)
    except:
        pass

    semaphore = asyncio.Semaphore(CONCURRENCY)
    pbar = tqdm(total=limit, desc=f"[*] {name}", unit="ads")

    last_count = 0
    while last_count < limit:
        await page.keyboard.press("End")
        await asyncio.sleep(2)
        cards = await page.query_selector_all("a[href*='/nabidka/']")
        if len(cards) == last_count:
            break
        pbar.update(min(len(cards) - last_count, limit - last_count))
        last_count = len(cards)

    cards = await page.query_selector_all("a[href*='/nabidka/']")
    signals_list = []
    batch_tasks = []
    for card in cards[:limit]:
        link = "https://www.startupjobs.cz" + await card.get_attribute("href")
        if CORE.is_known(link):
            continue

        # Specific Salary Metadata Extraction
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
        signals_list.append(sig)
        batch_tasks.append(scrape_detail(context, link, semaphore))

    if batch_tasks:
        results = await asyncio.gather(*batch_tasks)
        for i, (desc, bens) in enumerate(results):
            signals_list[i].description = desc
            signals_list[i].benefits = bens
            CORE.add_signal(signals_list[i])
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
    for _ in range(30):
        await page.keyboard.press("PageDown")
        await asyncio.sleep(1)

    cards = await page.query_selector_all("li.ais-Hits-item")
    signals_list = []
    batch_tasks = []
    for card in cards[:limit]:
        try:
            link_el = await card.query_selector("a")
            link = "https://www.welcometothejungle.com" + await link_el.get_attribute(
                "href"
            )
            if CORE.is_known(link):
                continue
            
            sig = JobSignal(
                title=await (await card.query_selector("h4")).inner_text(),
                company="WTTJ Partner",
                link=link,
                source=name,
                salary=None
            )
            signals_list.append(sig)
            batch_tasks.append(scrape_detail(context, link, semaphore))
            pbar.update(1)
        except:
            continue

    if batch_tasks:
        results = await asyncio.gather(*batch_tasks)
        for i, (desc, bens) in enumerate(results):
            signals_list[i].description = desc
            signals_list[i].benefits = bens
            CORE.add_signal(signals_list[i])
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
            if not cards:
                break
            signals_list = []
            batch_tasks = []
            for card in cards:
                link = "https://www.cocuma.cz" + await card.get_attribute("href")
                if CORE.is_known(link):
                    continue
                title_el = await card.query_selector(".job-thumbnail-title")
                comp_el = await card.query_selector(".job-thumbnail-company")
                
                sig = JobSignal(
                    title=await title_el.inner_text(),
                    company=await comp_el.inner_text(),
                    link=link,
                    source=name,
                    salary=None
                )
                signals_list.append(sig)
                batch_tasks.append(scrape_detail(context, link, semaphore))
            if batch_tasks:
                results = await asyncio.gather(*batch_tasks)
                for i, (desc, bens) in enumerate(results):
                    signals_list[i].description = desc
                    signals_list[i].benefits = bens
                    CORE.add_signal(signals_list[i])
            pbar.update(1)
        except:
            break
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
            link = (await (await card.query_selector("a")).get_attribute("href")).split(
                "?"
            )[0]
            if CORE.is_known(link):
                continue
            
            sig = JobSignal(
                title=await (await card.query_selector("h3")).inner_text(),
                company=await (await card.query_selector("h4")).inner_text(),
                link=link,
                source=name,
                description="LinkedIn Market Signal",
                salary=None,
                benefits=""
            )
            CORE.add_signal(sig)
            pbar.update(1)
        except:
            continue
    await context.close()


async def main():
    print("\n--- OMNISCRAPE v5.0: DEEP DETAIL EXTRACTION ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        await asyncio.gather(
            scrape_standard(
                browser,
                "Jobs.cz",
                "https://www.jobs.cz/prace/?page=",
                "article.SearchResultCard",
                "h2.SearchResultCard__title > a",
            ),
            scrape_standard(
                browser,
                "Prace.cz",
                "https://www.prace.cz/nabidky/?page=",
                "li.search-result__advert",
                "a.link",
            ),
            scrape_startupjobs(browser),
            scrape_wttj(browser),
            scrape_cocuma(browser),
            scrape_linkedin(browser),
        )
        await browser.close()
    print("\n--- INTEL CORE SYNCHRONIZED ---")


if __name__ == "__main__":
    asyncio.run(main())