
import asyncio
from playwright.async_api import async_playwright

async def debug_cocuma():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Check Page 13 (should work) and Page 14 (failed)
        for page_num in [13, 14, 15]:
            url = f"https://www.cocuma.cz/jobs/page/{page_num}/"
            print(f"\nNavigating to {url}")
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(2)
                
                cards = await page.query_selector_all('a.job-thumbnail')
                print(f"Found {len(cards)} cards")
                
                if not cards:
                    # Check if we reached the end
                    body_text = await page.evaluate("document.body.innerText")
                    if "stránka nenalezena" in body_text or "404" in body_text or "není k dispozici" in body_text:
                        print("Reached end of results (Expected)")
                    else:
                        print("Selectors failed but page exists. Possible layout change.")
                        print(f"Title: {await page.title()}")
                        # Dump some HTML
                        html = await page.content()
                        print(f"HTML snippet: {html[:500]}")
                
            except Exception as e:
                print(f"Error on Page {page_num}: {e}")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_cocuma())
