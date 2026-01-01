from playwright.sync_api import sync_playwright
import time

def inspect_site(name, url):
    print(f"Inspecting {name}...", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, timeout=30000)
            time.sleep(5) # Wait for hydration
            content = page.content()
            with open(f"debug_{name}.html", "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Saved debug_{name}.html", flush=True)
        except Exception as e:
            print(f"Failed to inspect {name}: {e}", flush=True)
        browser.close()

if __name__ == "__main__":
    inspect_site("startupjobs", "https://www.startupjobs.cz/nabidky")
    inspect_site("prace_cz", "https://www.prace.cz/nabidky/")
    inspect_site("fajnbrigady", "https://www.fajn-brigady.cz/brigady/")
    inspect_site("cocuma", "https://cocuma.cz/jobs")
    inspect_site("pracevnakupaku", "https://www.pracevnakupaku.cz/hledat")
