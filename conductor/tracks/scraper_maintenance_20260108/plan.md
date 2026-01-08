# Plan: Scraper Maintenance & Incident Resolution

This plan outlines the steps to resolve scraping incidents for WTTJ, Cocuma, and StartupJobs, and improve overall diagnostic logging.

## Phase 1: Diagnostics & Selector Audit [checkpoint: 11a3a12]
Focus on identifying the exact causes of failures through better logging and selector verification.

- [x] **Task: Enhance Diagnostic Logging** 25f334d
  - [x] Write Tests: Verify that failed extractions log specific missing attributes (title, link, etc.) instead of generic errors.
  - [x] Implement Feature: Update `BaseScraper` and individual scrapers to provide high-fidelity error messages.
- [x] **Task: WTTJ Selector Audit** 4a93a42
  - [x] Write Tests: Run a live selector check against WTTJ's current DOM to identify broken patterns.
  - [x] Implement Feature: Update `config/selectors.yaml` with resilient selectors for WTTJ.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Diagnostics & Selector Audit' (Protocol in workflow.md) 11a3a12

## Phase 2: Logic Fixes & Site Resilience [checkpoint: d2e4921]
Focus on fixing pagination and handling specific network exceptions.

- [x] **Task: Cocuma Pagination & Fallback Selectors**
  - [x] Write Tests: Verify the scraper can detect and click the Cocuma "Load More" button beyond page 10.
  - [x] Implement Feature: Refactor Cocuma logic to handle layout shifts on older pages and fix infinite scroll stalling.
- [x] **Task: StartupJobs Connection Resilience**
  - [x] Write Tests: Simulate `net::ERR_CONNECTION_CLOSED` and verify that specific retry logic triggers.
  - [x] Implement Feature: Add a targeted retry handler for connection resets in the `ScrapeEngine.scrape_detail` method.
- [~] **Task: WTTJ Rate Limit Tuning**
  - [ ] Write Tests: Verify that WTTJ requests maintain a randomized delay within the 3-7s window.
  - [ ] Implement Feature: Implement site-specific rate limiting overrides in `scraper.py`.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Logic Fixes & Site Resilience' (Protocol in workflow.md) d2e4921

## Phase 3: Final Verification [checkpoint: f3c1bc8]
Focus on confirming the yield increase and system stability.

- [x] **Task: Yield & Stability Benchmark** f3c1bc8
  - [x] Write Tests: Run a full scrape targeting 100+ jobs for WTTJ and full traversal for Cocuma.
  - [x] Implement Feature: Execute end-to-end verification and confirm zero circuit-breaker triggers.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Final Verification' (Protocol in workflow.md) f3c1bc8
