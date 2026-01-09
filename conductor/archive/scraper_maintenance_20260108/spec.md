# Specification: Scraper Maintenance & Incident Resolution

## 1. Overview
This track addresses scraping incidents identified during the last production run. We will focus on improving the reliability and data yield for WTTJ, Cocuma, and StartupJobs by refining selectors and enhancing error diagnostics.

## 2. Requirements

### 2.1 Functional Requirements
- **WTTJ Selector Update:** Investigate and update CSS selectors for Welcome to the Jungle. Implement more conservative rate limiting (randomized 3-7s delays) to avoid soft-blocking.
- **Cocuma Pagination Fix:** Debug the pagination/scroll logic for Cocuma to ensure it can reach beyond page 14. Add fallback selectors for job cards to handle legacy layout variations.
- **StartupJobs Connection Investigation:** Implement retry logic specifically for `net::ERR_CONNECTION_CLOSED` errors and log the specific browser context state when these occur.
- **Diagnostic Logging:** Transition from generic "Failed to process card" to specific messages (e.g., "Missing Title Selector in WTTJ", "Link Attribute Empty").

### 2.2 Non-Functional Requirements
- **Stability:** Zero "3 consecutive failures" terminations for Cocuma/WTTJ in a standard run.
- **Yield:** Targeted yield increase for WTTJ (aiming for >100 signals per run).

## 3. Acceptance Criteria
- [ ] WTTJ scraper successfully navigates past page 5 and collects valid signals.
- [ ] Cocuma scraper successfully navigates past page 14.
- [ ] Logs provide actionable insights for every skipped job listing.
- [ ] Circuit breaker only triggers on genuine site outages, not layout shifts.

## 4. Out of Scope
- Adding new scraping sources.
- Major database schema changes.
