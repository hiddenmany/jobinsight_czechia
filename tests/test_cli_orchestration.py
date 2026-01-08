import pytest
from unittest.mock import MagicMock, patch
from tools.whitelist_discovery import run_discovery

@patch('tools.whitelist_discovery.extract_candidates_from_db')
@patch('tools.whitelist_discovery.validate_candidates_with_llm')
@patch('tools.whitelist_discovery.update_classifiers_file')
@patch('tools.whitelist_discovery.generate_report')
def test_run_discovery_dry_run(mock_report, mock_update, mock_llm, mock_extract):
    """Test orchestration in dry-run mode."""
    # Setup mocks
    mock_extract.return_value = {"kubernetes": 10, "driver": 8}
    mock_llm.return_value = {"kubernetes": "Tech", "driver": "Non-Tech"}
    mock_update.return_value = True
    
    # Run
    summary = run_discovery(min_count=5, dry_run=True)
    
    # Assertions
    mock_extract.assert_called_with(min_count=5)
    mock_llm.assert_called()
    mock_report.assert_called()
    
    # Update should NOT be called in dry_run
    mock_update.assert_not_called()
    
    # In dry run, nothing is technically "added" to file, but candidates are identified
    # Let's assume summary reflects what WOULD be added
    # Or maybe we define "added" as persisted.
    # Logic: if dry_run, added=0.
    
    assert summary['added'] == 0
    assert summary['processed'] == 2

@patch('tools.whitelist_discovery.extract_candidates_from_db')
@patch('tools.whitelist_discovery.validate_candidates_with_llm')
@patch('tools.whitelist_discovery.update_classifiers_file')
@patch('tools.whitelist_discovery.generate_report')
def test_run_discovery_live(mock_report, mock_update, mock_llm, mock_extract):
    """Test orchestration in live mode."""
    # Setup mocks
    mock_extract.return_value = {"kubernetes": 10}
    mock_llm.return_value = {"kubernetes": "Tech"}
    mock_update.return_value = True
    
    # Run
    run_discovery(min_count=5, dry_run=False)
    
    # Update SHOULD be called
    mock_update.assert_called_once()
    args, _ = mock_update.call_args
    assert "kubernetes" in args[0]
