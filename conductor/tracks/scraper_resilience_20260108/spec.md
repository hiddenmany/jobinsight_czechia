# Specification: Scraper Resilience & Heartbeat Logic

## 1. Overview
This track addresses the issue where the StartupJobs scraper terminates prematurely (around 60% completion). The goal is to prevent environment-driven timeouts and ensure that all scraped data is preserved even if a crash occurs.

## 2. Requirements

### 2.1 Functional Requirements
- **Heartbeat Logging:** Implement a periodic "Heartbeat" message (e.g., every 30 seconds) during the scraping loop. This prevents the CLI/CI environment from killing the process due to perceived inactivity.
- **Incremental Data Persistence:** Refactor the scraper logic to commit batches of jobs to DuckDB immediately after they are parsed, rather than waiting for the entire source to finish.
- **Improved Error Catching:** Wrap the StartupJobs main loop in a robust try/except block to log the specific exception or signal that causes the 60% stall.

### 2.2 Non-Functional Requirements
- **Process Stability:** The scraper must complete 100% of available StartupJobs pages in the next run.
- **Log Transparency:** Heartbeat messages must include current progress (e.g., "Page 15/25 - Still active...").

## 3. Acceptance Criteria
- [ ] StartupJobs scraper finishes with "100% complete" or a graceful exit message.
- [ ] Logs show heartbeat messages during the long-running scrape.
- [ ] All signals scraped up to the point of any potential failure are verified to exist in `data/intelligence.db`.

## 4. Out of Scope
- Redesigning the StartupJobs selectors (unless they are the cause of the crash).
- Implementing multi-threading for this specific source.
