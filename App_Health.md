# App Health: Executive Talent Radar

## Architectural Integrity: 9.5/10
- Overhauled classification engine significantly reduces upstream data noise.
- System is now resilient to common Czech job market title inflation.

## Debt & Issues
- **Dependency:** Frontend relies on Plotly.js CDN.

## Recent Improvements
- **Refined Engineering Taxonomy:** Successfully resolved overlaps where non-IT engineers (Electrical, Mechanical, HVAC) were merging with Developers.
- **Improved Smart Matching:** Implemented word-boundary checks for sensitive keywords (controller, lead, manager) to prevent cross-category misclassifications (e.g., PLC Controller matching Finance).
- **Automation Routing:** Improved logic for Automation Engineers and PLC Programmers to ensure they land in General Engineering rather than IT or QA when in an industrial context.
- **Advanced Model Tiering:** Successfully transitioned to **Gemini 3 Pro** for market analysis and **Gemini 3 Flash** for automated taxonomy discovery.
- **Adaptive Taxonomy:** Discovered and integrated 12 new technical terms (SAP, Automation, Process Engineering) into the protection whitelist.
- **Verified Full Pipeline:** Completed a full scrape cycle (4,500+ jobs) and analysis generation with the new model configuration.
- Regional Intelligence: Implemented hub-specific benchmarking for Prague, Brno, and Ostrava.
- **Trend Logic:** Added support for multi-date salary movement analysis at the regional level.
- **AI-Powered Insights:** Integrated regional data into the Gemini prompt for weekly strategic reports.
- Finalized comprehensive job classification overhaul.
- Fixed high-priority misclassifications: Burger King/KFC (Hospitality), Bank Advisor (Finance), IT Admin (Developer).
- Implemented 'Sanity Check' layer to protect IT roles from industry-based downgrading.
- Refined overrides for Education, Legal, and Healthcare.
