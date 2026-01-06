import pytest
from classifiers import JobClassifier

@pytest.mark.parametrize("title, description, expected_role", [
    ("Python Developer", "Django backend", "Developer"),
    ("HR Generalist", "Recruiting and admin", "HR"),
    ("Senior Accountant", "Taxes and invoices", "Finance"),
    ("Store Manager", "Lidl prodejna", "Retail"), # Should be downgraded from Management
    ("Shift Leader", "Amazon warehouse", "Logistics"), # Should be downgraded
    ("Tech Lead", "Leading a team of engineers", "Developer"), # Should be reclassified to tech
])
def test_role_classification(title, description, expected_role):
    assert JobClassifier.classify_role(title, description) == expected_role

@pytest.mark.parametrize("title, description, expected_seniority", [
    ("Senior Python Dev", "", "Senior"),
    ("Junior HR", "", "Junior"),
    ("CTO", "Chief Technology Officer", "Executive"),
    ("Team Lead", "", "Lead"),
    ("Python Developer", "3 years experience", "Mid"), # Default
])
def test_seniority_detection(title, description, expected_seniority):
    assert JobClassifier.detect_seniority(title, description) == expected_seniority
