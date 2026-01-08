# Plan: Regional Salary Trend Analysis

This plan outlines the steps to implement regional salary trend analysis for Prague, Brno, and Ostrava.

## Phase 1: Data Normalization & Schema [checkpoint: 575c186]
Focus on ensuring location data is correctly captured and normalized.

- [x] **Task: Update Database Schema** c9ffaa8
  - [ ] Write Tests: Verify DuckDB schema can store normalized region and city data.
  - [ ] Implement Feature: Update `duckdb` schema to include `region` and `city` columns.
- [x] **Task: Implement Location Normalizer** 9245dba
  - [ ] Write Tests: Verify various city names map to correct regions (Prague, Brno, Ostrava).
  - [ ] Implement Feature: Create `tools/location_normalizer.py` to normalize scraped location strings.
- [x] **Task: Update Scraper Integration** c86b66f
  - [ ] Write Tests: Verify scraper passes location data to the normalizer.
  - [ ] Implement Feature: Update `parsers.py` and `scraper.py` to process location data during extraction.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Data Normalization & Schema' (Protocol in workflow.md) 575c186

## Phase 2: Regional Intelligence Engine [checkpoint: de2a0da]
Focus on calculating the metrics for each region.

- [x] **Task: Regional Stats Module** ed99b38
  - [ ] Write Tests: Verify median calculation logic for specific regions.
  - [ ] Implement Feature: Create `analyzer/regional_stats.py` to compute regional medians and volumes.
- [x] **Task: Trend Analysis Logic** de2a0da
  - [ ] Write Tests: Verify trend calculation over multiple scrape dates.
  - [ ] Implement Feature: Develop logic to compare current regional stats with historical data in DuckDB.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Regional Intelligence Engine' (Protocol in workflow.md) de2a0da

## Phase 3: Dashboard & Reporting [checkpoint: 765d7ea]
Focus on presenting the data to the user.

- [x] **Task: Regional Comparison Charts** aa4acd1
  - [ ] Write Tests: Verify data format for Streamlit/Plotly charts.
  - [ ] Implement Feature: Add interactive regional comparison charts to `app.py`.
- [x] **Task: AI-Powered Regional Insights** 765d7ea
  - [ ] Write Tests: Verify Gemini prompt includes regional data context.
  - [ ] Implement Feature: Update `llm_analyzer.py` to include regional trend summaries in weekly reports.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Dashboard & Reporting' (Protocol in workflow.md) 765d7ea
