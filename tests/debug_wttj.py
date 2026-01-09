
import asyncio
from playwright.async_api import async_playwright

async def debug_wttj():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        # Use page 3 where it hangs
        url = "https://www.welcometothejungle.com/cs/jobs?aroundQuery=Czechia&page=3"
        print(f"Navigating to {url}")
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(5)
            
            # Take screenshot
            await page.screenshot(path="debug_wttj_page3.png")
            print("Screenshot saved to debug_wttj_page3.png")
            
            # Check for cards manually
            cards = await page.evaluate("""() => {
                const items = document.querySelectorAll('li[data-testid="search-results-list-item-wrapper"]');
                return items.length;
            }""")
            print(f"Manual card count: {cards}")
            
            # Dump some text
            text = await page.evaluate("document.body.innerText")
            print(f"Text snippet: {text[:500]}")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_wttj())
