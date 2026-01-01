# App Health: JobsCzInsight

**Status:** 🟢 Fully Operational (v14.0)
**Last Updated:** 2025-12-31

## Overview
A high-end Executive Intelligence Dashboard designed for **iSTYLE HR**. It tracks 11 Czech job boards with deep content extraction to provide strategic "combat moves" against competitors.

## Core Capabilities
- **Deep Scrape Engine (v14.0):** Comprehensive market "vacuum" of Jobs.cz, Prace.cz, FajnBrigady, Cocuma, StartupJobs, WTTJ, and PraceVNakupnimCentru.
- **Deep Content Extraction:** Visits detail pages for every listing to extract full text for sentiment and keyword analysis.
- **Historical Intelligence:** Week-over-week trend tracking for salaries and vacancy volumes.
- **AI Strategy Lab:** Automatic JD blueprint generation (title, salary, hooks) based on current market leaders.
- **Local Talent War Drill-down:** City-specific SWOT analysis and salary benchmarking.
- **iSTYLE JD Audit:** Automated health check of iSTYLE listings with actionable fixes.

## Tech Stack
- **Backend:** Python, Playwright (Sync Mode), Pandas.
- **Frontend:** Streamlit (Custom Executive UI), Plotly.
- **Data:** Append-only CSV storage for historical analysis.

## Recently Added (v14.1)
- **Cloud Runner Integration:** Added GitHub Actions workflow (`.github/workflows/weekly_scrape.yml`) for automated weekly scraping and data updates.
- **Omniscrape v2:** Enhanced selectors for Prace.cz and FajnBrigady.
- **Deep Scrape Depth:** Configured for 100-page depth across all high-volume sources.
- **React-App Compatibility:** Specialized scrapers for Cocuma and StartupJobs infinite-scroll architectures.

## Next Steps
- [ ] **Data Cleaning Pipeline:** Refine deduplication logic for cross-posted ads between Jobs.cz and Prace.cz.
- [ ] **Deploy to Cloud:** Push the repository to GitHub to activate the automated scraping schedule.
