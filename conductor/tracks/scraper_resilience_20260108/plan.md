# Plan: Scraper Resilience & Heartbeat Logic

This plan outlines the steps to fix early termination in the StartupJobs scraper and implement heartbeat logging to prevent environment timeouts.

## Phase 1: Heartbeat & Logging Infrastructure [checkpoint: 2e35507]
Focus on preventing environment timeouts by maintaining an active signal.

- [x] **Task: Implement Heartbeat Utility** 1117027
  - [ ] Write Tests: Verify a simple timer-based heartbeat prints to stdout at specified intervals.
  - [ ] Implement Feature: Create a `Heartbeat` utility in `scraper_utils.py` that handles periodic logging during long-running tasks.
- [x] **Task: Integrate Heartbeat into Scraper Loop** 2e35507
  - [ ] Write Tests: Verify that calling the heartbeat during a long-running mock loop produces the expected logs.
  - [ ] Implement Feature: Update the main loop in `scraper.py` to trigger the heartbeat during page navigation and item processing.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Heartbeat & Logging Infrastructure' (Protocol in workflow.md) 2e35507

## Phase 2: Incremental Persistence & Error Handling [checkpoint: 3e74418]
Focus on data safety and ensuring that partial progress is never lost.

- [x] **Task: Refactor Batch Persistence** 3e74418
  - [ ] Write Tests: Verify that data is written to DuckDB in small chunks rather than one giant transaction at the end.
  - [ ] Implement Feature: Modify `scraper.py` to call `add_signal` immediately after every page or batch of jobs is scraped.
- [x] **Task: Graceful StartupJobs Exception Handling** 3e74418
  - [ ] Write Tests: Verify that a simulated timeout or exception in one page doesn't kill the entire scraper process.
  - [ ] Implement Feature: Wrap StartupJobs-specific logic in a specialized try/except block with detailed logging of the failure point.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Incremental Persistence & Error Handling' (Protocol in workflow.md) 3e74418

## Phase 3: Final Verification
Focus on proving the 100% completion goal in the target environment.

- [x] **Task: End-to-End Scrape Test** 8059219
  - [x] Write Tests: Run a limited, high-speed scrape of StartupJobs to verify heartbeats and persistence logic.
  - [x] Implement Feature: Execute a full StartupJobs scrape and monitor for the previously observed 60% bottleneck.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Final Verification' (Protocol in workflow.md)
