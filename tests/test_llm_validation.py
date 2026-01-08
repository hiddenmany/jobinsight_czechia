import pytest
import os
from unittest.mock import MagicMock, patch
from tools.whitelist_discovery import validate_candidates_with_llm

@patch('tools.whitelist_discovery.genai')
@patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"})
def test_llm_validation_tech(mock_genai):
    """Test that LLM validation correctly parses 'Tech' response."""
    # Mock client
    mock_client = MagicMock()
    mock_genai.Client.return_value = mock_client
    
    # Mock response
    mock_response = MagicMock()
    mock_response.text = """
    kubernetes: Tech
    driver: Non-Tech
    """
    mock_client.models.generate_content.return_value = mock_response
    
    candidates = ["kubernetes", "driver"]
    results = validate_candidates_with_llm(candidates)
    
    assert results["kubernetes"] == "Tech"
    assert results["driver"] == "Non-Tech"
