
import asyncio
from playwright.async_api import async_playwright

async def inspect_card():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = "https://www.welcometothejungle.com/cs/jobs?aroundQuery=Czechia&page=1"
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(2)
            
            card = await page.query_selector('li[data-testid="search-results-list-item-wrapper"]')
            if card:
                # Dump the innerHTML of the card
                html = await card.inner_html()
                print("CARD HTML:")
                print(html)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_card())
