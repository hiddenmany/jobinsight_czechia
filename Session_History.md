# Session History: Executive Talent Radar

## Session: 2026-01-08 - Currency, Paths, Tech Stack UI, Bonus & Engineering Taxonomy
**Objective:** Replace hardcoded values, visualize tech_status, enhance salary parsing, and improve classification.

### 1. Currency Configuration (config/currency_rates.yaml)
- **CNB Rates:** Created config file with official Czech National Bank exchange rates.
- **Multi-Currency:** Added support for EUR, USD, GBP, PLN, CHF conversion.
- **Update Guide:** Included source link for weekly rate updates.

### 2. Parser Enhancement (parsers.py)
- **Dynamic Loading:** Implemented `_load_currency_rates()` with lazy-load caching.
- **Fallback Defaults:** Graceful degradation if config file is missing.
- **Extended Support:** Added GBP (£), PLN (zł), CHF detection patterns.

### 3. Centralized Settings (settings.py) [NEW]
- **Settings Class:** Created single source of truth for all paths (DB, cache, config, templates).
- **Environment Overrides:** Support for `JOBSCZINSIGHT_DB_PATH` and `JOBSCZINSIGHT_CACHE_PATH` environment variables.
- **Directory Management:** `ensure_dirs()` method to create required directories.
- **Migration:** Updated `analyzer.py` and `generate_report.py` to use Settings.

### 4. Tech Stack Health Visualization [NEW]
- **KPI Calculation:** Added Modern/Dinosaur/Stable counts and health score (Modern rate - 2×Dinosaur rate).
- **Dashboard Card:** New KPI card in `executive_dashboard.html` showing:
  - 258 Modern jobs (green) / 11 Dinosaur jobs (red)
  - 6.3% Modern rate with color-coded health indicator
- **Health Labels:** "Zdravý" (>5), "Neutrální" (0-5), "Zastaralý" (<0)

### 5. Bonus Detection (parsers.py) [NEW]
- **`parse_with_bonus()` Method:** Enhanced parsing that separates base salary from bonus components.
- **Pattern Support:** Czech (bonus, prémie, 13./14. plat) and English (annual bonus, performance bonus).
- **Negative Context:** Correctly handles "bez bonusu" / "without bonus".

### 6. Engineering Sub-Taxonomy (classifiers.py) [NEW]
- **General Engineering Category:** Added new category for non-IT engineering roles.
- **Keywords:** HVAC, vzduchotechnik, klimatizace, mechanical engineer, electrical engineer, konstruktér, procesní inženýr, quality engineer, validation engineer, etc.
- **Enhanced Clean-up:** Improved Developer filtering with HVAC/MEP detection and better IT vs non-IT separation.
- **IT Protection:** Preserved Python, Java, DevOps, Cloud roles as Developer while routing HVAC/mechanical/electrical to General Engineering.

### 7. Remote Location Deduplication (analyzer.py) [FIX]
- **Enhanced Hash:** Updated `get_content_hash()` to handle Remote/generic locations.
- **Link Suffix:** Includes last 50 chars of job URL for unique identification.
- **Extended Content:** Uses 750 chars of description (vs 500) for generic locations.
- **Generic Detection:** Handles 'remote', 'cz', 'czechia', 'home office', 'anywhere'.

### 8. Threshold Tuning (parsers.py) [FIX]
- **Hourly Threshold:** Increased from 1,000 to 3,500 CZK/hour to accommodate executive consultants.
- **Daily Threshold:** Increased from 10,000 to 25,000 CZK/day for senior contractor rates.
- **Documentation:** Added inline comments explaining threshold validation against CZ market 2026.
- **Named Constants:** Replaced magic numbers with `HOURLY_THRESHOLD`, `DAILY_THRESHOLD`, `MONTHLY_HOURS`, `WORKING_DAYS`.

### 9. Test Fixes & Stabilization [FIX]
- **StartupJobs Shorthand:** Fixed bug where range detection skipped shorthand logic (e.g. 60-80 -> 60k-80k).
- **Classifier Edge Cases:** Fixed 7 regressions in role classification (Shift Leader, Tech Lead, Grafik směn, Quality Control).
- **Unreachable Code:** Removed early return in `classifiers.py` that was blocking QA/Developer cleanup logic.
- **EUR Test:** Updated expected value to match dynamic rate (25.2).

### 10. Verification
- **Status:** PASS - All 114 tests passing (100% Green). All 8 roadmap items completed.

---

## Session: 2026-01-08 (Part 3) - Adaptive Taxonomy & GitHub Automation
**Objective:** Implement an automated technical keyword discovery system and integrate it into the GitHub Actions pipeline.

### 1. Adaptive Taxonomy (Whitelist Auto-update) [TRACK COMPLETE]
- **Core Utility (tools/whitelist_discovery.py):**
    - **Extraction Engine:** Implemented n-gram (1-3 word) extraction from job titles and descriptions currently classified as 'Other'.
    - **Statistical Significance:** Added frequency thresholds and ratio-based significance scoring.
    - **Contextual Proximity:** Implemented a proximity scorer that boosts terms appearing near known technologies (e.g., "Kubernetes" near "Java").
- **LLM Validation Logic:**
    - **Tiered Model Strategy:** Integrated **Gemini 1.5 Flash** (via `google-genai` SDK) for high-speed, cost-effective classification of discovered terms into "Tech", "Non-Tech", or "Unrelated".
    - **Prompt Engineering:** Optimized prompts to handle multi-lingual (CZ/EN) technical terms.
- **Automated Code Patching:**
    - **Regex Patcher:** Developed a robust mechanism to programmatically update the `tech_protection` whitelist in `classifiers.py` with high-confidence terms.
    - **Idempotency:** Ensures no duplicate entries are added to the code.
- **Reporting:**
    - **Markdown Generator:** Automated generation of `report/whitelist_candidates.md` to track newly added terms and candidates for manual review.

### 2. GitHub CI/CD Enhancement
- **Workflow Update (.github/workflows/weekly_scrape.yml):**
    - **Discovery Step:** Added a new job step to run the whitelist discovery tool in `live` mode after each weekly scrape.
    - **Persistence:** Configured the workflow to automatically commit and push changes to `classifiers.py` and the new discovery report back to the repository.
- **Secret Integration:** Confirmed `GEMINI_API_KEY` mapping from GitHub Secrets to the automation environment.

### 3. Verification & Testing
- **Unit Testing:** Created comprehensive test suites:
    - `tests/test_whitelist_extraction.py`: Verified n-gram logic and frequency counting.
    - `tests/test_llm_validation.py`: Verified Gemini integration and response parsing.
    - `tests/test_code_patcher.py`: Verified safe file modification.
    - `tests/test_cli_orchestration.py`: Verified dry-run vs live execution modes.
- **Manual Verification:** Executed full CLI orchestration against a 3,000+ job backup database, confirming successful candidate extraction and report generation.

### 4. Verification Results
- **Extraction Yield:** Successfully processed 745 unique candidates from existing "Other" listings.
- **Automation Status:** Whitelist discovery is now a permanent part of the weekly data refresh cycle.

---

## Pending & Future Focus (Roadmap)
The following items were identified in the final audit but not yet implemented:

### 1. Classification & Keyword Refinement
- ~~**Engineering Sub-Taxonomy:** Separate "General Engineering" from "IT Engineering" more cleanly.~~ ✅ **DONE** (2026-01-08)
- ~~**Whitelist Auto-update:** Create a mechanism to flag high-frequency terms in 'Other' that look like Tech roles.~~ ✅ **DONE** (2026-01-08) - Implemented Adaptive Taxonomy with Gemini 1.5 Flash
- **Advanced Grouping:** Enhance `whitelist_discovery.py` to group related terms (e.g., "React.js", "React JS", "ReactJS") before LLM validation to save tokens.

### 2. Salary & Currency
- ~~**Dynamic Conversion:** Replace static EUR/USD rates in parsers.py.~~ ✅ **DONE** (2026-01-08)
- ~~**Bonus Detection:** Improve range detection to explicitly handle "bonus" or "13th month" keywords.~~ ✅ **DONE** (2026-01-08)

### 3. Dashboard/UI
- ~~**Signal Visualization:** Update the frontend to display the ghost_score and tech_status.~~ ✅ **DONE** (2026-01-08)
- ~~**Location Mapping:** Improve handling of "Remote" as a location in the deduplication hash.~~ ✅ **DONE** (2026-01-08)

### 4. Technical Debt
- ~~**Path Config:** Centralize the hardcoded "data/" and "config/" paths into a single Settings class.~~ ✅ **DONE** (2026-01-08)
- ~~**Threshold Tuning:** Validation against high-end executive contractor rates.~~ ✅ **DONE** (2026-01-08)
- **Database Standardization:** Resolve inconsistency between `intelligence.db` and `jobs.db` naming conventions across environments.
- **Git LFS Audit:** Ensure the active database is correctly tracked and synced between local and CI environments.

---

## Session: 2026-01-09 - Gemini 3 Upgrade & Model Tiering
**Objective:** Transition to the latest Gemini 3 models and implement a tiered strategy for analysis and taxonomy categorization.

### 1. Advanced Model Tiering [NEW]
- **Market Analysis:** Upgraded `llm_analyzer.py` to use **Gemini 3 Pro** (`gemini-3-pro-preview`) for high-tier strategic insights.
- **Taxonomy Categorization:** Transitioned `tools/whitelist_discovery.py` to use **Gemini 3 Flash** (`gemini-3-flash-preview`) for efficient, low-latency technical term identification.
- **Environment Integration:** Added `load_dotenv()` to `whitelist_discovery.py` to ensure seamless API key access.

### 2. Adaptive Taxonomy (Gemini 3 Flash)
- **Live Discovery:** Successfully ran the whitelist discovery tool in `live` mode.
- **Yield:** Identified and integrated 12 new high-confidence technical terms into `classifiers.py` (e.g., SAP, Automatizace, Procesní technik).
- **Quality Control:** Verified that non-tech terms (BOZP, Management, Consulting) are correctly filtered by the new Flash model.

### 3. Full Pipeline Verification
- **Large-Scale Scrape:** Executed a full scrape cycle, successfully harvesting **4,598 active job signals** across 5 sources.
- **Fresh Insights:** Generated a new market report (`public/index.html`) using fresh Gemini 3 Pro analysis.
- **Database Integrity:** Successfully completed database vacuuming and cleanup of 0 expired listings.

### 4. Verification Results
- **Status:** PASS - Scraper, Analyzer, and Whitelist Discovery all operational with the new tiered model configuration.
- **App Health:** Updated `App_Health.md` to reflect the 100% successful transition to Gemini 3.

---
