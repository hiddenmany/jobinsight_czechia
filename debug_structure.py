from playwright.sync_api import sync_playwright
import time

def save_html(url, filename):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, timeout=60000)
            time.sleep(5) # Wait for JS to load
            content = page.content()
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Saved {filename}")
        except Exception as e:
            print(f"Error saving {filename}: {e}")
        browser.close()

# StartupJobs
print("Fetching StartupJobs...")
save_html("https://www.startupjobs.cz/nabidky", "debug_startupjobs.html")
# We need a detail page URL. I'll try to find one from the main page content later, 
# or just pick a likely one if I can see the links. 
# For now, just the main page to see the list structure and links.

# Cocuma
print("Fetching Cocuma...")
save_html("https://www.cocuma.cz/jobs/", "debug_cocuma.html")
