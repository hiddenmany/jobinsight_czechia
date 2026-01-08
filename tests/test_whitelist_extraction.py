import pytest
from unittest.mock import MagicMock
import pandas as pd
from tools.whitelist_discovery import extract_candidates_from_text, calculate_significance, calculate_proximity_score

def test_extract_ngrams_basic():
    """Test basic 1-3 gram extraction."""
    text = "Java developer with python skills"
    # Expected: java, developer, with, python, skills, java developer, developer with...
    # We focus on the logic, let's assume we want valid words.
    candidates = extract_candidates_from_text([text])
    
    assert "java" in candidates
    assert "python" in candidates
    assert "java developer" in candidates
    
def test_frequency_counting():
    """Test that terms are counted correctly."""
    texts = ["Java developer", "Java developer", "Python developer"]
    candidates = extract_candidates_from_text(texts)
    
    assert candidates["java developer"] == 2
    assert candidates["python developer"] == 1
    assert candidates["developer"] == 3

def test_stopword_filtering():
    """Test that common stopwords are ignored."""
    texts = ["developer and manager", "skills in java"]
    candidates = extract_candidates_from_text(texts)
    
    assert "and" not in candidates
    assert "in" not in candidates
    assert "java" in candidates
    assert "skills" in candidates

def test_significance_calculation():
    """Test significance score (frequency / total_docs)."""
    # If "java" appears in 5 out of 10 docs, score is 0.5
    freq = 5
    total_docs = 10
    score = calculate_significance(freq, total_docs)
    assert score == 0.5

def test_threshold_filtering():
    """Test filtering by absolute count."""
    pass

def test_proximity_score_match():
    """Test that a term near a context keyword gets a boost."""
    text = "Experience with Java and Kubernetes is required."
    term = "kubernetes"
    context_keywords = ["java", "python"]
    # "java" is near "kubernetes"
    score = calculate_proximity_score(text, term, context_keywords, window=3)
    assert score > 0.0

def test_proximity_score_no_match():
    """Test that a term far from keywords gets 0 score."""
    text = "We are hiring. Java is great. Also we need a driver."
    term = "driver"
    context_keywords = ["java"]
    # "driver" is far from "java"
    score = calculate_proximity_score(text, term, context_keywords, window=2)
    assert score == 0.0