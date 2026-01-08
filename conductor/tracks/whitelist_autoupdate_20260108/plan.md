# Implementation Plan - Whitelist Auto-update

## Phase 1: Candidate Discovery Logic
- [x] Task: Create extraction utility
    - [x] Sub-task: Write Tests: Create `tests/test_whitelist_extraction.py` with test cases for n-gram extraction and frequency counting.
    - [x] Sub-task: Implement Feature: Create `tools/whitelist_discovery.py` (or a helper module) with `extract_candidates_from_db()` using DuckDB text search/regex.
- [x] Task: Implement Contextual Proximity Scoring
    - [x] Sub-task: Write Tests: Add tests for `calculate_proximity_score` ensuring it boosts terms near known tech keywords.
    - [x] Sub-task: Implement Feature: Add scoring logic to `whitelist_discovery.py`.
- [x] Task: Integrate LLM Validation
    - [x] Sub-task: Write Tests: Create `tests/test_llm_validation.py` mocking the Gemini API response to verify batching and classification logic.
    - [x] Sub-task: Implement Feature: Implement `validate_candidates_with_llm()` using `google-genai` and `gemini-1.5-flash-lite` (or similar efficient model).
- [x] Task: Conductor - User Manual Verification 'Candidate Discovery Logic' (Protocol in workflow.md) [checkpoint: ee4f541]

## Phase 2: Reporting & Code Patching
- [x] Task: Implement Code Patcher
    - [x] Sub-task: Write Tests: Create `tests/test_code_patcher.py` ensuring `classifiers.py` is read and updated correctly without syntax errors.
    - [x] Sub-task: Implement Feature: Implement `update_classifiers_file()` using robust regex replacement for the `tech_protection` list.
- [x] Task: Generate Markdown Report
    - [x] Sub-task: Write Tests: Verify the report generator produces valid Markdown structure from a list of result objects.
    - [x] Sub-task: Implement Feature: Implement `generate_report()` to output `report/whitelist_candidates.md`.
- [x] Task: Conductor - User Manual Verification 'Reporting & Code Patching' (Protocol in workflow.md) [checkpoint: 2cbc776]
- [ ] Task: Conductor - User Manual Verification 'Reporting & Code Patching' (Protocol in workflow.md)

## Phase 3: Integration & Final Polish
- [x] Task: CLI Orchestration
    - [x] Sub-task: Write Tests: Test the main execution flow (mocking DB and LLM) to ensure arguments and modes (auto-update vs report-only) work.
    - [x] Sub-task: Implement Feature: Finalize `tools/whitelist_discovery.py` main block to chain Extraction -> Validation -> Reporting -> Patcher.
- [x] Task: Conductor - User Manual Verification 'Integration & Final Polish' (Protocol in workflow.md) [checkpoint: 4e4e5a9]
- [ ] Task: Conductor - User Manual Verification 'Integration & Final Polish' (Protocol in workflow.md)
