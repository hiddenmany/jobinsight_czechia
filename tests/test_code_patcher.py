import pytest
import os
import tempfile
from tools.whitelist_discovery import update_classifiers_file

# Sample content of classifiers.py
SAMPLE_CLASSIFIERS = """
class JobClassifier:
    def _classify_role_keywords(self):
        # ...
        if matched_role in ['Developer', 'Analyst']:
             tech_protection = ['software', 'php', 'java', 'c#']
             if any(kw in text for kw in tech_protection):
                  return matched_role
"""

def test_code_patcher_updates_list():
    """Test that tech_protection list is updated with new terms."""
    # Create temp file
    # We close it so other processes/functions can open it
    fd, tmp_path = tempfile.mkstemp(suffix='.py')
    with os.fdopen(fd, 'w') as tmp:
        tmp.write(SAMPLE_CLASSIFIERS)
        
    try:
        new_terms = ['kubernetes', 'docker']
        
        # Pass path to function
        success = update_classifiers_file(new_terms, file_path=tmp_path)
        assert success
        
        with open(tmp_path, 'r') as f:
            content = f.read()
            
        assert "'kubernetes'" in content
        assert "'docker'" in content
        assert "'php'" in content # Original kept
        
        # Verify syntax (simple check)
        compile(content, tmp_path, 'exec')
        
    finally:
        os.remove(tmp_path)

def test_code_patcher_no_duplicates():
    """Test that existing terms are not duplicated."""
    fd, tmp_path = tempfile.mkstemp(suffix='.py')
    with os.fdopen(fd, 'w') as tmp:
        tmp.write(SAMPLE_CLASSIFIERS)
        
    try:
        new_terms = ['php', 'docker'] # php exists
        
        success = update_classifiers_file(new_terms, file_path=tmp_path)
        assert success
        
        with open(tmp_path, 'r') as f:
            content = f.read()
            
        # Count occurrences
        assert content.count("'php'") == 1
        assert "'docker'" in content
        
    finally:
        os.remove(tmp_path)
