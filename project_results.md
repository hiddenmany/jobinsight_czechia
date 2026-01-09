# Project: Executive Talent Radar (self_command)

## Overview
A Gemini CLI Extension project focused on creating a localized, deduplicated, and accurate dashboard for analyzing job market signals in Czechia. The dashboard is delivered as a standalone HTML file (public/index.html) with embedded data.

## Stated Goals
- Send commands to Gemini CLI using tmux methodology (Phase 2 goal).
- Ensure high-quality engineering hygiene (docstrings, logging, unit tests).
- Provide a localized (Czech) and accurate data visualization.

## Phases and Work Done
- **Phase 1: Scaffolding & Data Setup**
    - Initial dashboard structure.
    - Integration of RAW_DATA_SOURCE from CSV/DB.
- **Phase 2: Data Cleaning & Localization**
    - Implemented runtime JavaScript deduplication (~656 duplicates removed).
    - Full Czech localization of UI, filters, and charts.
- **Phase 3: Advanced Automated Classification (NEW)**
    - Comprehensive overhaul of 'classifiers.py'.
    - Implemented multi-layered 'Sanity Check' logic to protect IT role integrity.
    - Fixed significant industry overlaps (Burger King/KFC to Hospitality, Bank Advisors to Finance, Ph.D. to Education).
    - Eliminated major misclassifications in Analyst and Healthcare categories.

## Custom Code & Descriptions
- **Deduplication Logic:** Injected JS in index.html that uses a Set-based hash check.
- **Plotly Optimization:** Modified Plotly configurations for better label readability.
- **Python Classifiers:** Overhauled 'classifiers.py' with industry-specific exclusion rules and prioritized taxonomy matching.

## FAQ
**Q: How accurate is the role classification now?**
A: Significantly improved. We use a hybrid approach with keyword priority and negative context checks to separate Tech roles from industry-specific context.

**Q: Why were fast food workers in Healthcare?**
A: Due to 'medical certificate' (zdravotní průkaz) mentions. This is now fixed with negative lookahead logic.

## Troubleshooting
- **Classification issues:** If a role is still misclassified, add the specific title to the exclusion list in 'classifiers.py'.

## Reproduction Steps
1. Use Python duckdb library to manage 'data/intelligence.db'.
2. Run analysis using the updated 'classifiers.py'.
