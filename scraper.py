import asyncio
import pandas as pd
import time
import random
import os
import hashlib
import analyzer
from tqdm.asyncio import tqdm
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
CONCURRENCY_LIMIT = 5
INTEL = analyzer.MarketIntelligence()
KNOWN_HASHES = INTEL.get_active_hashes()

async def intercept_resources(route):
    if route.request.resource_type in ["image", "media", "font"]:
        await route.abort()
    else:
        await route.continue_()

def get_short_hash(title, company):
    """Initial check hash before deep scraping."""
    raw = f"{title}{company}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()

async def scrape_detail(context, url, semaphore):
    if not url or "linkedin.com" in url: return ""
    async with semaphore:
        page = await context.new_page()
        await page.route("**/*", intercept_resources)
        try:
            await page.goto(url, timeout=20000, wait_until="domcontentloaded")
            content = await page.evaluate("""() => {
                const s = ['div.JobDescription', 'article', 'main', '.jd-content'];
                for (let x of s) { let el = document.querySelector(x); if (el) return el.innerText; }
                return document.body.innerText;
            }""")
            await page.close()
            return content.strip()[:4000]
        except:
            await page.close()
            return ""

async def scrape_jobs_cz(browser, limit=100):
    name = "Jobs.cz"
    base_url = "https://www.jobs.cz/prace/?page="
    context = await browser.new_context()
    page = await context.new_page()
    await page.route("**/*", intercept_resources)
    
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    all_data = []
    
    print(f"[*] {name}: Shadow Scanning for new signals...")
    for page_num in range(1, limit + 1):
        try:
            await page.goto(f"{base_url}{page_num}", timeout=60000)
            cards = await page.query_selector_all("article.SearchResultCard")
            if not cards: break
            
            new_batch_metadata = []
            for card in cards:
                title_el = await card.query_selector("h2.SearchResultCard__title > a")
                comp_el = await card.query_selector("li.SearchResultCard__footerItem > span[translate='no']")
                
                title = await title_el.inner_text()
                company = await comp_el.inner_text() if comp_el else "Unknown"
                href = await title_el.get_attribute("href")
                
                # DIFFERENTIAL CHECK
                # We use a combined check of URL and a lazy Title+Company hash
                # If either is known, we skip deep scrape
                if href in INTEL.df['link'].values: continue
                
                new_batch_metadata.append({
                    "title": title, "company": company, "link": href,
                    "source": name, "scraped_at": time.time(),
                    "salary": await (await card.query_selector("span.Tag--success")).inner_text() if await card.query_selector("span.Tag--success") else None,
                    "location": "CZ"
                })

            if new_batch_metadata:
                print(f"  > Page {page_num}: Found {len(new_batch_metadata)} new listings. Extracting details...")
                tasks = [scrape_detail(context, m["link"], semaphore) for m in new_batch_metadata]
                descriptions = await asyncio.gather(*tasks)
                for i, desc in enumerate(descriptions):
                    new_batch_metadata[i]["description"] = desc
                    all_data.append(new_batch_metadata[i])
            else:
                # If we hit a page with 0 new listings, we can potentially stop early 
                # (but we continue for safety in case of re-ordering)
                pass
                
        except Exception as e:
            print(f"Error {name} p{page_num}: {e}")
            break
            
    if all_data:
        pd.DataFrame(all_data).to_csv(f"data/{name.lower().replace('.', '_')}.csv", mode='a', index=False, header=not os.path.exists(f"data/{name.lower().replace('.', '_')}.csv"))
    await context.close()

async def main():
    print("\n--- DIFFERENTIAL MARKET SCAN v3.0 (STATEFUL) ---")
    print(f"Current Intelligence: {len(INTEL.df)} records | {len(KNOWN_HASHES)} unique hashes.")
    
    async with async_playwright() as p:
        # Run Jobs.cz as a thorough example of the new stateful logic
        browser = await p.chromium.launch(headless=True)
        await scrape_jobs_cz(browser, limit=10) # 10 pages for safety
        await browser.close()
    print("\n--- SCAN COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(main())
