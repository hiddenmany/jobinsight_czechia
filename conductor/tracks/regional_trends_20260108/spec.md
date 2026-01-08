# Specification: Regional Salary Trend Analysis

## 1. Overview
This track enhances the existing Czech Market Intelligence platform to provide granular regional insights, specifically focusing on salary trends in Prague, Brno, and Ostrava. This will allow users to compare compensation across major tech hubs.

## 2. Requirements

### 2.1 Functional Requirements
- **Regional Data Extraction:** Update scraper and parsers to accurately extract and normalize location data for Prague, Brno, and Ostrava.
- **Regional Statistics Engine:** Develop logic to calculate median salaries and job volume specifically for these three regions.
- **Trend Analysis:** Implement a time-series analysis (weekly/monthly) to track salary movement in each region.
- **Dashboard Integration:** Add new visualizations to the Streamlit dashboard to display regional comparisons.

### 2.2 Non-Functional Requirements
- **Data Quality:** Regional classification accuracy must be >95%.
- **Performance:** Regional dashboard filters should load in <2 seconds.
- **Verification:** All new logic must have >80% test coverage.

## 3. Technical Design
- **Data Schema:** Add `region` and `city` columns to the DuckDB `jobs` table if not already present.
- **Normalizer:** Create a lookup table/logic to map various location strings (e.g., "Praha 4", "Prague") to normalized region IDs.
- **Aggregation:** Use DuckDB SQL queries for efficient regional grouping and median calculation.
- **Visualization:** Use Plotly or Altair for interactive regional charts.
