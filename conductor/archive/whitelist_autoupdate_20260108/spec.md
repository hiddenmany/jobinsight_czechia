# Specification: Whitelist Auto-update (Tech Role Discovery)

## 1. Overview
The goal of this track is to implement an automated mechanism to discover missing technical keywords and roles currently categorized as "Other". It uses statistical analysis and LLM verification to propose and (semi-automatically) apply updates to the `tech_protection` whitelist in `classifiers.py`, ensuring the "Developer" and other tech-related categories remain accurate as the market evolves.

## 2. Functional Requirements
### 2.1 Candidate Discovery
- **Hybrid Frequency Detection:** Scan all jobs categorized as "Other" and extract frequent n-grams (1-3 words). Terms must meet both an absolute count (e.g., >5 occurrences) and a statistical significance threshold relative to the total "Other" population.
- **Contextual Proximity Check:** Prioritize terms that frequently appear near existing tech keywords (e.g., "zkušenost s", "znalost", or established techs like "Java", "AWS").

### 2.2 Validation Engine
- **LLM Verification (Gemini):** Send extracted candidate terms to Gemini (using a cost-effective model like `gemini-1.5-flash-lite`) to classify them as "Tech Skill/Role", "Generic Professional", or "Unrelated".
- **Confidence Scoring:** Assign a confidence score based on LLM feedback and contextual indicators.

### 2.3 Update & Reporting
- **Semi-Automatic Updates:** 
    - Terms with "High Confidence" (as determined by LLM + Context) are automatically appended to the `tech_protection` list in `classifiers.py`.
    - Code modification must be robust (e.g., using regex to find and update the `tech_protection = [...]` line).
- **Markdown Reporting:** Generate `report/whitelist_candidates.md` detailing:
    - Newly added (High Confidence) terms.
    - Flagged candidates (Medium/Low Confidence) for manual review.
    - Statistical metrics for each term (frequency, context).

## 3. Non-Functional Requirements
- **Efficiency:** The discovery script should run against the existing DuckDB database without requiring a full re-scrape.
- **Cost Control:** LLM prompts must be batched to minimize API calls and token usage.
- **Idempotency:** Re-running the tool should not result in duplicate entries in the whitelist.

## 4. Acceptance Criteria
- [ ] A new utility script `tools/whitelist_discovery.py` exists.
- [ ] Running the script identifies at least 5 relevant tech terms from current "Other" data (if present).
- [ ] `classifiers.py` is successfully updated programmatically when high-confidence terms are found.
- [ ] `report/whitelist_candidates.md` is generated with a clear breakdown of findings.
- [ ] Unit tests verify the statistical extraction and code-update logic.

## 5. Out of Scope
- Automatic removal of terms from the whitelist.
- Real-time classification updates during the scraping process (this is a post-processing tool).
- Full re-classification of the entire database after whitelist update (this remains a separate manual or triggered task).
