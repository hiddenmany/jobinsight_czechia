from playwright.sync_api import sync_playwright
import pandas as pd
import time
import random
import os
import sys
import asyncio
import re
from tqdm import tqdm

# Globální konfigurace
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def get_page_context(browser):
    return browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={"width": 1920, "height": 1080},
        extra_http_headers={"Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8"}
    ).new_page()

def scrape_detail(page, url):
    """Hloubkové vytěžení textu inzerátu."""
    if not url or url == "N/A" or "linkedin.com" in url: return ""
    try:
        # random delay to mimic human behavior
        time.sleep(random.uniform(0.2, 0.5))
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        content = page.evaluate("""() => {
            const sels = ['div.JobDescription', 'article', 'main', '.jd-content', '.search-result__advert__box__item--description', '.job-detail__description', '.job-body'];
            for (let s of sels) {
                let el = document.querySelector(s);
                if (el) return el.innerText;
            }
            return document.body.innerText;
        }""")
        return content.strip()[:5000]
    except: return ""

def save_batch(data, name, mode='a'):
    if not data: return
    path = f"data/{name.lower().replace('.', '_')}.csv"
    os.makedirs("data", exist_ok=True)
    df = pd.DataFrame(data)
    header = not os.path.exists(path) or mode == 'w'
    df.to_csv(path, mode=mode, index=False, header=header)

# --- PRODUCTION ENGINES ---

def scrape_jobs_cz(limit=100):
    name = "Jobs.cz"
    base_url = "https://www.jobs.cz/prace/?page="
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = get_page_context(browser)
        det_page = get_page_context(browser)
        pbar = tqdm(total=limit, desc=f"[*] {name}", unit="pg")
        for page_num in range(1, limit + 1):
            try:
                page.goto(f"{base_url}{page_num}", timeout=60000)
                page.wait_for_selector("article.SearchResultCard", timeout=15000)
                cards = page.query_selector_all("article.SearchResultCard")
                if not cards: break
                batch = []
                for card in cards:
                    try:
                        title_el = card.query_selector("h2.SearchResultCard__title > a")
                        link = title_el.get_attribute("href")
                        comp_el = card.query_selector("li.SearchResultCard__footerItem > span[translate='no']")
                        sal_el = card.query_selector("span.Tag--success")
                        loc_el = card.query_selector("li[data-test='serp-locality']")
                        
                        batch.append({
                            "title": title_el.inner_text().strip(),
                            "company": comp_el.inner_text().strip() if comp_el else "Unknown",
                            "salary": sal_el.inner_text().strip() if sal_el else None,
                            "description": scrape_detail(det_page, link),
                            "link": link, "source": name, "scraped_at": time.time(), 
                            "location": loc_el.inner_text().strip() if loc_el else "CZ"
                        })
                    except: continue
                save_batch(batch, name, 'w' if page_num == 1 else 'a')
                pbar.update(1)
            except Exception as e:
                print(f"\n[!] {name} error on page {page_num}: {e}")
                break
        pbar.close()
        browser.close()

def scrape_prace_cz(limit=100):
    name = "Prace.cz"
    base_url = "https://www.prace.cz/nabidky/?page="
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = get_page_context(browser)
        det_page = get_page_context(browser)
        pbar = tqdm(total=limit, desc=f"[*] {name}", unit="pg")
        for page_num in range(1, limit + 1):
            try:
                page.goto(f"{base_url}{page_num}", timeout=60000)
                page.wait_for_selector("li.search-result__advert", timeout=15000)
                cards = page.query_selector_all("li.search-result__advert")
                if not cards: break
                batch = []
                for card in cards:
                    try:
                        title_el = card.query_selector("a.link")
                        link = title_el.get_attribute("href")
                        if not link.startswith("http"): link = "https://www.prace.cz" + link
                        comp_el = card.query_selector(".search-result__advert__box__item--company")
                        sal_el = card.query_selector(".search-result__advert__box__item--salary")
                        loc_el = card.query_selector(".search-result__advert__box__item--location")
                        
                        batch.append({
                            "title": title_el.inner_text().strip(),
                            "company": comp_el.inner_text().strip() if comp_el else "Unknown",
                            "salary": sal_el.inner_text().strip() if sal_el else None,
                            "description": scrape_detail(det_page, link),
                            "link": link, "source": name, "scraped_at": time.time(),
                            "location": loc_el.inner_text().strip() if loc_el else "CZ"
                        })
                    except: continue
                save_batch(batch, name, 'w' if page_num == 1 else 'a')
                pbar.update(1)
            except Exception as e:
                print(f"\n[!] {name} error on page {page_num}: {e}")
                break
        pbar.close()
        browser.close()

def scrape_startupjobs(limit=1000):
    name = "StartupJobs"
    url = "https://www.startupjobs.cz/nabidky"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = get_page_context(browser)
        det_page = get_page_context(browser)
        page.goto(url)
        try: page.get_by_text("Přijmout").click(timeout=5000)
        except: pass
        
        pbar = tqdm(total=limit, desc=f"[*] {name}", unit="ads")
        last_count = 0
        while last_count < limit:
            page.keyboard.press("End")
            time.sleep(2)
            try:
                btn = page.get_by_text("Načíst další stránku")
                if btn.is_visible(): 
                    btn.click(force=True)
                    time.sleep(3)
            except: pass
            cards = page.query_selector_all("a[href*='/nabidka/']")
            if len(cards) == last_count: break
            pbar.update(min(len(cards) - last_count, limit - last_count))
            last_count = len(cards)
        
        batch = []
        for card in cards[:limit]:
            try:
                link = "https://www.startupjobs.cz" + card.get_attribute("href")
                salary = None
                items = card.query_selector_all("li")
                for item in items:
                    txt = item.inner_text()
                    if "Kč" in txt or "EUR" in txt:
                        salary = txt.strip()
                        break

                batch.append({
                    "title": card.inner_text().split("\n")[0],
                    "company": "Startup", "salary": salary,
                    "description": scrape_detail(det_page, link),
                    "link": link, "source": name, "scraped_at": time.time(), "location": "CZ"
                })
            except: continue
        save_batch(batch, name, 'w')
        pbar.close()
        browser.close()

def scrape_cocuma(limit=100):
    name = "Cocuma"
    base_url = "https://www.cocuma.cz/jobs/?page="
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = get_page_context(browser)
        det_page = get_page_context(browser)
        pbar = tqdm(total=limit, desc=f"[*] {name}", unit="pg")
        seen_links = set()
        for page_num in range(1, limit + 1):
            try:
                page.goto(f"{base_url}{page_num}/", timeout=60000)
                cards = page.query_selector_all("a.job-thumbnail")
                if not cards: break
                batch = []
                for card in cards:
                    link = "https://www.cocuma.cz" + card.get_attribute("href")
                    if link in seen_links: continue
                    seen_links.add(link)
                    title_el = card.query_selector(".job-thumbnail-title")
                    comp_el = card.query_selector(".job-thumbnail-company")
                    title_text = title_el.inner_text().strip() if title_el else ""
                    full_title_attr = card.get_attribute("title") or ""
                    salary = None
                    sal_match = re.search(r'(\d[\d\s\.]*\d)\s*[-–]\s*(\d[\d\s\.]*\d)\s*(Kč|CZK|EUR)', full_title_attr + " " + title_text)
                    if sal_match: salary = sal_match.group(0)
                    batch.append({
                        "title": title_text, "company": comp_el.inner_text().strip() if comp_el else "Unknown",
                        "salary": salary, "description": scrape_detail(det_page, link),
                        "link": link, "source": name, "scraped_at": time.time(), "location": "CZ"
                    })
                if not batch: break
                save_batch(batch, name, 'w' if page_num == 1 else 'a')
                pbar.update(1)
            except: break
        pbar.close()
        browser.close()

def scrape_wttj(limit=500):
    name = "WTTJ"
    url = "https://www.welcometothejungle.com/cs/jobs?aroundQuery=Czechia"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = get_page_context(browser)
        det_page = get_page_context(browser)
        page.goto(url)
        pbar = tqdm(total=limit, desc=f"[*] {name}", unit="ads")
        # Scroll logic
        last_count = 0
        for _ in range(50):
            page.keyboard.press("PageDown")
            time.sleep(1.5)
            cards = page.query_selector_all("li.ais-Hits-item")
            if len(cards) >= limit or len(cards) == last_count: break
            last_count = len(cards)
        
        batch = []
        for card in cards[:limit]:
            try:
                title_el = card.query_selector("h4")
                link_el = card.query_selector("a")
                link = "https://www.welcometothejungle.com" + link_el.get_attribute("href")
                batch.append({
                    "title": title_el.inner_text().strip(),
                    "company": "WTTJ Partner", "salary": None,
                    "description": scrape_detail(det_page, link),
                    "link": link, "source": name, "scraped_at": time.time(), "location": "CZ"
                })
                pbar.update(1)
            except: continue
        save_batch(batch, name, 'w')
        pbar.close()
        browser.close()

def scrape_linkedin(limit=200):
    name = "LinkedIn"
    url = "https://www.linkedin.com/jobs/search?keywords=&location=Czechia&geoId=106057199"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = get_page_context(browser)
        page.goto(url)
        pbar = tqdm(total=limit, desc=f"[*] {name}", unit="ads")
        for _ in range(20):
            page.keyboard.press("End")
            time.sleep(2)
        cards = page.query_selector_all("div.base-card")
        batch = []
        for card in cards[:limit]:
            try:
                batch.append({
                    "title": card.query_selector("h3").inner_text().strip(),
                    "company": card.query_selector("h4").inner_text().strip(),
                    "salary": None, "description": "LinkedIn Market Signal", 
                    "link": card.query_selector("a").get_attribute("href").split('?')[0],
                    "source": name, "scraped_at": time.time(), "location": "CZ"
                })
                pbar.update(1)
            except: continue
        save_batch(batch, name, 'w')
        pbar.close()
        browser.close()

def run_all():
    print("\n--- OMNISCRAPE 2026: MAXIMUM MARKET DEPTH ---")
    if os.path.exists("data"):
        for f in os.listdir("data"):
            if f.endswith(".csv"): os.remove(os.path.join("data", f))
    
    scrape_jobs_cz(limit=100)
    scrape_prace_cz(limit=100)
    scrape_startupjobs(limit=1000)
    scrape_cocuma(limit=100)
    scrape_wttj(limit=500)
    scrape_linkedin(limit=200)
    print("\n--- DATA HARVEST COMPLETE ---")

if __name__ == "__main__":
    run_all()
