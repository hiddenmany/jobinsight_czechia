# JobsCzInsight: Czech Market Intelligence

**A high-end Executive Intelligence Dashboard designed for HR strategy and market analysis.**

This tool tracks major Czech job boards (Jobs.cz, Prace.cz, StartupJobs, Cocuma, WTTJ, LinkedIn) to provide strategic "combat moves" against competitors. It extracts deep content from job listings to analyze salaries, benefits, and keyword trends.

## 🚀 Core Capabilities

- **Deep Scrape Engine:** "Vacuums" the market, visiting detail pages to extract full description text.
- **Strategic Intelligence:** Analyzes salary data (median vs average), benefit keywords (Remote, English, etc.), and market sentiment.
- **Historical Tracking:** Tracks market signals over time to identify trends.
- **Cloud Automation:** Runs automatically every week via GitHub Actions to keep data fresh without manual intervention.

## 🛠 Tech Stack

- **Python 3.10+**
- **Playwright:** For robust, headless browser scraping (handles infinite scroll & dynamic JS).
- **Streamlit:** For the interactive executive dashboard.
- **Pandas & Plotly:** For data processing and visualization.
- **GitHub Actions:** For automated weekly data harvesting.

## 📦 Installation & Local Usage

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/hiddenmany/jobinsight_czechia.git
    cd jobinsight_czechia
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```

3.  **Run the Dashboard:**
    ```bash
    streamlit run app.py
    ```

4.  **Run the Scraper Manually:**
    ```bash
    python scraper.py
    ```

## ☁️ Cloud Automation

The scraper is configured to run automatically using **GitHub Actions**.

- **Schedule:** Every Monday at 08:00 UTC.
- **Workflow:** `.github/workflows/weekly_scrape.yml`
- **Actions:**
    1.  Runs `scraper.py` to get fresh data.
    2.  Commits new CSVs to the repo.
    3.  Generates a static HTML report.
    4.  Deploys the report to GitHub Pages.

## 🌐 Live Static Snapshot

This repo automatically publishes a static "Market Snapshot" report after every scrape.
To enable it:
1.  Go to your GitHub Repo -> **Settings** -> **Pages**.
2.  Under "Build and deployment", select **Source**: `Deploy from a branch`.
3.  Select **Branch**: `gh-pages` / `(root)`.
4.  Your report will be live at: `https://hiddenmany.github.io/jobinsight_czechia/`

## 📊 Data Sources

- **Jobs.cz**
- **Prace.cz**
- **StartupJobs**
- **Cocuma**
- **Welcome to the Jungle (WTTJ)**
- **LinkedIn** (Market Signal only)

---
*Maintained by hiddenmany*
