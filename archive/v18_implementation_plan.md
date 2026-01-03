# v18.0 Implementation Plan - All 47 Fixes

## Execution Strategy
Due to scope (47 fixes, ~2000 LOC changes), implementing in tested stages:

### Stage 1: Infrastructure & Config ✓
- Utilities module (retry, sanitize, UA rotation) 
- Config validation
- Constants extraction
- Fallback cities moved to config

### Stage 2: Scraper Core Improvements
- Rate limiting (all scrapers)
- Retry mechanisms
- Specific exception handling
- Circuit breaker
- Graceful shutdown
- LinkedIn detail scraping fix
- Memory leak fixes

### Stage 3: Analyzer & Performance  
- Race condition fix (is_known)
- Compiled regex patterns
- Named SQL parameters
- Connection pooling considerations

### Stage 4: Test Coverage
- Scraper unit tests
- Integration tests
- Config validation tests
- Database operation tests
- Extended salary parser tests

### Stage 5: Code Quality & Observability
- Extract god methods
- Add type hints
- Add docstrings
- Metrics collection
- Improved logging

### Stage 6: Configuration & Legal
- Selector improvements
- Robots.txt compliance
- Request attribution

## Testing Protocol
After each stage:
1. Syntax validation (py_compile)
2. Unit test execution
3. Small-scale scrape test (2-3 pages)
4. Performance validation
5. Git commit with detailed message

## Risk Mitigation
- Backups created (scraper.py.v17_backup, analyzer.py.v17_backup)
- Each stage can be rolled back independently
- Progressive testing prevents cascade failures
- All changes version controlled

