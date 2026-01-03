# Czech Market Intelligence

[![Market Scraper](https://github.com/hiddenmany/jobinsight_czechia/actions/workflows/weekly_scrape.yml/badge.svg)](https://github.com/hiddenmany/jobinsight_czechia/actions/workflows/weekly_scrape.yml)
[![Live Dashboard](https://img.shields.io/badge/Live-HR_Intelligence-0055FF?style=for-the-badge&logo=github)](https://hiddenmany.github.io/jobinsight_czechia/)

**v1.0 HR Intelligence Edition** - Actionable market intelligence for HR professionals and employers.

## 🌐 Live Market Overview
The latest market intelligence is automatically updated every Monday:
👉 **[https://hiddenmany.github.io/jobinsight_czechia/](https://hiddenmany.github.io/jobinsight_czechia/)**

---

## 🚀 Core Capabilities

### v1.0 HR Intelligence Features (NEW)
- **Role Classification:** Salary breakdown by job function (Developer, Analyst, Sales, HR, etc.)
- **Seniority Detection:** Compensation by level (Junior, Mid, Senior, Lead, Executive)
- **Skill Premium Analysis:** Which technical skills command higher pay
- **Enhanced Reporting:** Visual HR Intelligence dashboard

### Market Analysis
- **Deep Scrape Engine:** Extracts full job descriptions from detail pages
- **Semantic Engine (NER Lite):** Analyzes tech stack modernity and workplace toxicity
- **DuckDB Persistence:** High-performance analytical database
- **Strategic Intelligence:** Salary benchmarks, benefit analysis, contract types
- **Cloud Automation:** Weekly GitHub Actions scrapes

## 🛠 Tech Stack

- **Python 3.10+**
- **Playwright:** Headless browser scraping
- **DuckDB:** Local analytical database
- **Streamlit:** Interactive dashboard
- **Pandas & Plotly:** Data processing and visualization
- **GitHub Actions:** Automated weekly harvesting

## 📦 Installation & Local Usage

1. **Clone the repository:**
    ```bash
    git clone https://github.com/hiddenmany/jobinsight_czechia.git
    cd jobinsight_czechia
    ```

2. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```

3. **Run the Dashboard:**
    ```bash
    streamlit run app.py
    ```

4. **Run the Scraper Manually:**
    ```bash
    python scraper.py
    ```

5. **Generate Static Report:**
    ```bash
    python generate_report.py
    ```

## ☁️ Cloud Automation

- **Schedule:** Every Monday at 08:00 UTC
- **Workflow:** `.github/workflows/weekly_scrape.yml`
- **Actions:** Scrape → Generate Report → Deploy to GitHub Pages

## 📊 Data Sources

| Source | Coverage | Notes |
|--------|----------|-------|
| Jobs.cz | Full | Primary source |
| Prace.cz | Full | Largest volume |
| StartupJobs | Full | Startup ecosystem |
| Cocuma | Full | Tech-focused |
| WTTJ | Partial | Low signal yield |
| LinkedIn | Signal only | Rate limited |

---

## 📈 HR Intelligence Metrics

The v1.0 report includes:
- **Salary by Role:** PM, Developer, Analyst, Sales, etc.
- **Salary by Seniority:** Junior → Mid → Senior → Lead → Executive progression
- **Tech Stack Gap:** Modern vs Stable vs Legacy
- **Contract Reality:** HPP vs IČO vs Brigáda distribution
- **Top Innovators:** Companies hiring in modern tech stacks

---
*Maintained by hiddenmany • v1.0 HR Intelligence Edition*
