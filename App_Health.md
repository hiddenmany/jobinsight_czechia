# JobsCzInsight App Health

## Status: REPORTING FIXES 🛠️
**Last Verified:** 2026-01-02
**Version:** 16.3 (Data Integrity Patch)

## Core Metrics
- **Visuals:** [PASS] - Electric Blue accents + Soft Black palette.
- **Scraper:** [PASS] - Cocuma base_url fixed, Limits increased, Cleanup threshold optimized (180m).
- **Database:** [SYNCING] - Local scrape completing, Cloud report being patched.
- **Reporting:** [FIXED] - Solved "Unknown Employer" & "Negative HPP" bugs.

## Recent Upgrades
- **Cocuma:** Fixed `base_url` (removed `?page=`) and increased limit to 50 to capture full market.
- **Cleanup:** Increased expiry threshold to 180 minutes to prevent data loss during long runs.
- **WTTJ/LinkedIn:** Improved infinite scroll logic (increased scroll count/wait times).
- **Selectors:** Hardened `Jobs.cz` company extraction to ignore "Praha/Location" tags.
- **Analyzer:** Rewrote Contract Split logic to be mutually exclusive (Priority: ICO > Brigada > HPP).
- **Visualization:** Added sample size (n=X) to Salary Chart for context.
- **Reliability:** Auto-trigger `reanalyze_all()` if tech signals are missing in report generation.

## Current Activity
- **Patch Deployment:** Pushing fixes for the "Bad Report" anomalies detected by user.
- **Local Data:** Scrape near completion, will generate clean local report to verify.

## Known Risks
- **LinkedIn Rate Limits:** Still a bottleneck.
- **WTTJ Latency:** Optimized with resource blocking in `selectors.yaml`.