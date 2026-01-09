
import asyncio
from playwright.async_api import async_playwright
import yaml
import os

async def audit_wttj():
    config_path = "config/selectors.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    wttj_config = config['scrapers']['WTTJ']
    base_url = wttj_config['base_url']
    card_sel = wttj_config['card']
    title_sel = wttj_config['title']
    link_sel = wttj_config['link']
    
    print(f"Auditing WTTJ at {base_url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            for page_num in range(1, 4):
                url = f"{base_url}&page={page_num}"
                print(f"\nChecking Page {page_num}: {url}")
                
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                # Wait for cards
                try:
                    await page.wait_for_selector(card_sel, timeout=30000)
                except Exception as e:
                    print(f"TIMEOUT on Page {page_num}: {e}")
                    # Save screenshot for debugging
                    await page.screenshot(path=f"debug_wttj_page_{page_num}.png")
                    continue
                
                cards = await page.query_selector_all(card_sel)
                print(f"Found {len(cards)} cards")
                
                if not cards:
                    print(f"FAILURE: No cards on Page {page_num}")
                    continue
                    
                # Check first card of this page
                card = cards[0]
                title_el = await card.query_selector(title_sel)
                link_el = await card.query_selector(link_sel)
                company_el = None
                for sel in wttj_config['company_selectors']:
                    company_el = await card.query_selector(sel)
                    if company_el: 
                        print(f"Company selector '{sel}' worked")
                        break
                
                print(f"Title: {title_el is not None}, Link: {link_el is not None}, Company: {company_el is not None}")
                
            return True
        except Exception as e:
            print(f"Audit error: {e}")
            return False
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(audit_wttj())
