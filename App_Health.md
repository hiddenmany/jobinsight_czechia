# JobsCzInsight App Health

## Status: PRODUCTION-READY v1.3 🚀
**Last Verified:** 2026-01-03 (Cloud Run)
**Version:** 1.3 (Stable Scraper Edition)

### Latest Health Check (Cloud) ✅
```
Signals Harvested:        4,612 (Fresh Snapshot)
Database (Local):         7,131 (Historical)
Report Generation:        SUCCESS ✓
Dashboard:                ONLINE (GitHub Pages)
```

### Source Breakdown (Cloud Run)
| Source | Signals | Status |
|--------|---------|--------|
| **Prace.cz** | 2,948 | ✅ Excellent |
| **Jobs.cz** | 1,223 | ✅ Excellent |
| **Cocuma** | 239 | ✅ Full Coverage |
| **StartupJobs** | 174 | ⚠️ Partial (Context Issues) |
| **WTTJ** | 30 | ⚠️ Low Yield |
| **LinkedIn** | 0 | ❌ Blocked (Cloud IP) |

## v1.3 - Stable Scraper Edition

### INFRASTRUCTURE UPGRADES (2026-01-03) ✅
- **Persistence:** Enabled GitHub Actions caching for `data/intelligence.db` to persist historical data across cloud runs.
- **Proxy Support:** Added `LINKEDIN_PROXY` support to `scraper.py` to allow bypassing LinkedIn authwalls if a proxy is provided.

### FIXES APPLIED (2026-01-03) ✅
- **Report Generation:** Fixed Jinja2 template error (`TypeError: not all arguments converted`) by using Python string formatting (`"{:,}".format()`) instead of invalid filter usage. Also fixed path resolution for templates and output.
- **Navigation Fix:** Resolved `net::ERR_FAILED` by preventing `intercept_noise` from aborting main navigation requests.
- **StartupJobs Stability:** Added robust retries for "Execution context destroyed" errors.
- **WTTJ & LinkedIn:** Fixed infinite scroll and selectors.

## Data Quality
- **Role Coverage:** 100% classified
- **Seniority Coverage:** 100% classified
- **Salary Data:** 44% (Very High for CZ Market)

## Known Limitations
- **Cloud vs Local:** Cloud runs start with an empty DB (4.5k signals), while local runs persist history (7k+ signals).
- **LinkedIn:** Highly sensitive to Cloud IPs (Azure/AWS), resulting in 0 signals on GitHub Actions despite working locally.
- **Skill Premiums:** Low coverage (tech keywords missing in many JDs)
