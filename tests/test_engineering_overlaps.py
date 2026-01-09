import pytest
from classifiers import JobClassifier

@pytest.mark.parametrize("title, description, expected_role", [
    ("Electrical Engineer", "Design of electrical systems", "General Engineering"),
    ("Elektroprojektant", "Projekce silnoproudu", "General Engineering"),
    ("Strojní inženýr", "Mechanical engineering tasks", "General Engineering"),
    ("Konstruktér", "Mechanical design using CAD", "General Engineering"),
    ("HVAC Inženýr", "Design of heating and cooling", "General Engineering"),
    ("Process Engineer", "Optimization of manufacturing processes", "Manufacturing"), # Per logic in classifiers.py
    ("Industrial Engineer", "Work in factory", "Manufacturing"),
    ("PLC Programmer", "Programming industrial controllers", "General Engineering"), # Often overlaps with Developer but should probably be Engineering
    ("Automation Engineer", "Industrial automation", "General Engineering"),
])
def test_engineering_overlaps(title, description, expected_role):
    # Note: PLC Programmer might currently be classified as Developer because of 'Programmer'
    # but the goal is to see where it lands and if it's correct for this project's taxonomy.
    # Actually, ROLE_TAXONOMY['Developer'] has 'programátor', but 'General Engineering' has 'application engineer', 'procesní inženýr'.
    result = JobClassifier.classify_role(title, description)
    assert result == expected_role
