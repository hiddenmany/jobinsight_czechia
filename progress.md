
## 2026-01-09: Engineering Classification Refinement
- **Issue:** Non-IT engineers (Electrical, Mechanical, HVAC) were occasionally misclassified as Developers or other roles.
- **Fix:** 
    - Updated `ROLE_TAXONOMY` in `classifiers.py` to better separate `General Engineering` and `Manufacturing`.
    - Added explicit keywords like `elektroprojektant`, `plc programmer`, `automation engineer` to `General Engineering`.
    - Enhanced `smart_match` with word-boundary checks for keywords like `controller`, `lead`, `manager` to prevent false positives (e.g., "PLC Controller" matching "Finance/Controller").
    - Added comprehensive test suite `tests/test_engineering_overlaps.py` covering 9 engineering specific cases.
- **Verification:** All 9 new tests passed, and all 11 original classification tests passed.

## 2026-01-07: Teya Job Classification Fix
- **Investigation:** User reported suspicious "HR" jobs for "Storyous | Teya".
- **Analysis:** Identified 'intelligence.db' as DuckDB. Inspected records and confirmed titles were "Field Sales Agent" (Sales), not HR.
- **Fix:** Patched 'public/index.html' to reclassify 5 "HR" entries for "Storyous | Teya" to "Sales".
- **Infrastructure:** Confirmed DB type as DuckDB for future reference.
- Finalized comprehensive job classification overhaul in classifiers.py. 
- Fixed high-priority misclassifications: Burger King/KFC (Hospitality), Bank Advisor (Finance), IT Admin (Developer). 
- Implemented Sanity Check layer to protect IT roles from industry-based downgrading. 
- Refined overrides for Education, Legal, and Healthcare. 
