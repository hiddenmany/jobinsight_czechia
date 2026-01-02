# App Health Check - JobsCzInsight

**Date:** 2026-01-02
**Status:** Healthy

## Recent Updates
- **Cocuma Scraper Fix:** Resolved an issue where Cocuma listings were failing to be scraped due to a hardcoded domain in `StartupJobsScraper`. The scraper now dynamically handles Cocuma URLs. Added robust `wait_for_selector` logic to prevent race conditions during page load.
- **Visual Fix (Charts):** Corrected `generate_report.py` to use `automargin=True` for Plotly charts.
- **Visual Fix (Layout):** Updated `templates/report.html` to handle text overflows.
- **Process Management:** Handled a locked DuckDB database file.

## Current State
- **Data Pipeline:** Functional. `analyzer.py` correctly reads from `data/intelligence.db`.
- **Report Generation:** `generate_report.py` runs successfully.
- **Frontend:** `templates/report.html` is robust against long text and responsive.

## Next Steps
- Verify the weekly automated scrape on GitHub Actions.