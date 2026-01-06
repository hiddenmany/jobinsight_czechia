# Czech Market Intelligence

[![Market Scraper](https://github.com/hiddenmany/jobinsight_czechia/actions/workflows/weekly_scrape.yml/badge.svg)](https://github.com/hiddenmany/jobinsight_czechia/actions/workflows/weekly_scrape.yml)
[![Live Dashboard](https://img.shields.io/badge/Live-HR_Intelligence-0055FF?style=for-the-badge&logo=github)](https://hiddenmany.github.io/jobinsight_czechia/)

**v1.5 AI-Powered Edition** - Actionable market intelligence for HR professionals and employers with advanced LLM insights.

## 🌐 Live Market Overview
The latest market intelligence is automatically updated every Monday:
👉 **[https://hiddenmany.github.io/jobinsight_czechia/](https://hiddenmany.github.io/jobinsight_czechia/)**

<!-- START_STATS -->

### 📊 Current Market Pulse (Auto-Updated)
| Metric | Value | Context |
|--------|-------|---------|
| **Active Job Listings** | `3,935` | Across major Czech portals |
| **Professional Median** | `35 407 CZK` | Tech, Management, & White-collar roles |
| **National Est. Median** | `29 920 CZK` | All roles, Full-time (HPP only) |
| **Top 3 Roles** | Manufacturing, Developer, Other | High volume demand |
| **Last Updated** | 2026-01-06 09:43 UTC | |

> *Note: 'National Est. Median' approximates ČSÚ methodology (HPP only), while 'Professional Median' reflects the target audience of this report.*

<!-- END_STATS -->

---

## 🚀 Core Capabilities

### v1.5 Updates: AI-Powered Market Intelligence (NEW)
- **Advanced LLM Integration:** Upgraded to modern `google-genai` SDK with `gemini-3-pro-preview` for sophisticated market analysis
- **Dual-Median Statistics:** Professional Median (tech/white-collar) + National Estimated Median (ČSÚ methodology)
- **Multi-Currency Support:** Automatic EUR and USD conversion to CZK during salary parsing
- **Auto-Updated README:** Live statistics injection via GitHub Actions
- **Enhanced Security:** Local `.env` support for API key management

### v1.1: Enhanced Stability
- **Robust Scraping:** Fixed critical navigation blocks on StartupJobs (avoiding `net::ERR_FAILED`)
- **Improved Coverage:** Correctly extracts links from Cocuma's non-standard cards
- **Better Parsing:** Updated WTTJ selectors to match current site layout
- **Consistent Metrics:** Unified extraction statistics across all sources

### v1.0: HR Intelligence Features
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
- **Google Gemini AI:** Advanced market insights powered by `gemini-3-pro-preview`
- **GitHub Actions:** Automated weekly harvesting

## 📈 Dual-Median Methodology

This project provides **two distinct salary metrics** to serve different analytical needs:

### 1. Professional Median (81,250 CZK)
**Target Audience:** HR professionals, tech recruiters, and white-collar job seekers

**Included Roles:**
- Developer, Analyst, Management, PM, Sales, HR
- Marketing, Designer, QA, Finance, Legal
- Education, Technical Specialists, Electromechanics

**Purpose:** Reflects the actual compensation landscape for skilled professional roles. This is the metric most relevant for tech hiring, salary benchmarking, and competitive analysis in professional services.

### 2. National Estimated Median (31,421 CZK)
**Target Audience:** Economists, policy researchers, national labor market analysis

**Methodology:** Approximates the Czech Statistical Office (ČSÚ) approach:
- **Filters for Full-Time Employment (HPP)** only
- **Excludes:**
  - Part-time workers (Brigáda, DPP, DPČ)
  - Contractors and self-employed (IČO, OSVČ, Fakturace, Živnost)

**Important Context:**
- This metric shows the **advertised floor salary** in job postings
- ČSÚ's official median (~41,000 CZK) reflects **actual paid wages** including bonuses, overtime, and benefits
- The ~10,000 CZK gap is expected because:
  1. Job ads typically show base salary ranges (minimum guarantees)
  2. Actual compensation includes variable pay not advertised upfront
  3. Our data captures "entry offers" rather than "settled wages"

**Why Two Medians?**
- **For HR Strategy:** Use Professional Median to stay competitive in skilled labor markets
- **For Economic Research:** Use National Median to understand broad labor market trends
- **For Policy Analysis:** Compare both to understand the professional vs. general labor market gap

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

The report includes:
- **Salary by Role:** PM, Developer, Analyst, Sales, etc.
- **Salary by Seniority:** Junior → Mid → Senior → Lead → Executive progression
- **Tech Stack Gap:** Modern vs Stable vs Legacy
- **Contract Reality:** HPP vs IČO vs Brigáda distribution
- **Top Innovators:** Companies hiring in modern tech stacks

---
*Maintained by hiddenmany • v1.1 Stable Scraper Edition*
