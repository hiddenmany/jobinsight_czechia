# JobsCzInsight App Health

## Status: HIGH-VOLUME MODE 🚀
**Last Verified:** 2026-01-02
**Version:** 16.4 (Volume & Depth Expansion)

## Core Metrics
- **Visuals:** [PASS] - Electric Blue accents + Soft Black palette.
- **Scraper:** [PASS] - Deep Scrape enabled (Jobs/Prace: 2000, Others: 500). Concurrency increased (10).
- **Database:** [SYNCING] - Large batch ingestion in progress.
- **Reporting:** [FIXED] - Solved "Unknown Employer" & "Negative HPP" bugs.

## Recent Upgrades
- **Volume Expansion:** Increased scrape depth to 2000 for Jobs.cz/Prace.cz and 500 for secondary sources.
- **Throughput:** Increased detail-scrape concurrency to 10 to maintain speed with higher volume.
- **Cocuma:** Fixed `base_url` (removed `?page=`) and increased limit to 500 (max available).
- **Cleanup:** 180-minute threshold to support the longer, deeper scrape sessions.
- **Analyzer:** Rewrote Contract Split logic to be mutually exclusive (Priority: ICO > Brigada > HPP).
- **Visualization:** Added sample size (n=X) to Salary Chart for context.
- **Reliability:** Auto-trigger `reanalyze_all()` if tech signals are missing in report generation.

## Current Activity
- **Patch Deployment:** Pushing fixes for the "Bad Report" anomalies detected by user.
- **Local Data:** Scrape near completion, will generate clean local report to verify.

## Known Risks
- **LinkedIn Rate Limits:** Still a bottleneck.
- **WTTJ Latency:** Optimized with resource blocking in `selectors.yaml`.