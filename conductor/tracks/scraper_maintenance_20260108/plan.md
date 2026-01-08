# Plan: Scraper Maintenance & Incident Resolution

This plan outlines the steps to resolve scraping incidents for WTTJ, Cocuma, and StartupJobs, and improve overall diagnostic logging.

## Phase 1: Diagnostics & Selector Audit
Focus on identifying the exact causes of failures through better logging and selector verification.

- [x] **Task: Enhance Diagnostic Logging** 25f334d
  - [x] Write Tests: Verify that failed extractions log specific missing attributes (title, link, etc.) instead of generic errors.
  - [x] Implement Feature: Update `BaseScraper` and individual scrapers to provide high-fidelity error messages.
- [x] **Task: WTTJ Selector Audit** 4a93a42
  - [x] Write Tests: Run a live selector check against WTTJ's current DOM to identify broken patterns.
  - [x] Implement Feature: Update `config/selectors.yaml` with resilient selectors for WTTJ.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Diagnostics & Selector Audit' (Protocol in workflow.md)

## Phase 2: Logic Fixes & Site Resilience
Focus on fixing pagination and handling specific network exceptions.

- [ ] **Task: Cocuma Pagination & Fallback Selectors**
  - [ ] Write Tests: Verify the scraper can detect and click the Cocuma "Load More" button beyond page 10.
  - [ ] Implement Feature: Refactor Cocuma logic to handle layout shifts on older pages and fix infinite scroll stalling.
- [ ] **Task: StartupJobs Connection Resilience**
  - [ ] Write Tests: Simulate `net::ERR_CONNECTION_CLOSED` and verify that specific retry logic triggers.
  - [ ] Implement Feature: Add a targeted retry handler for connection resets in the `ScrapeEngine.scrape_detail` method.
- [ ] **Task: WTTJ Rate Limit Tuning**
  - [ ] Write Tests: Verify that WTTJ requests maintain a randomized delay within the 3-7s window.
  - [ ] Implement Feature: Implement site-specific rate limiting overrides in `scraper.py`.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Logic Fixes & Site Resilience' (Protocol in workflow.md)

## Phase 3: Final Verification
Focus on confirming the yield increase and system stability.

- [ ] **Task: Yield & Stability Benchmark**
  - [ ] Write Tests: Run a full scrape targeting 100+ jobs for WTTJ and full traversal for Cocuma.
  - [ ] Implement Feature: Execute end-to-end verification and confirm zero circuit-breaker triggers.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Final Verification' (Protocol in workflow.md)
