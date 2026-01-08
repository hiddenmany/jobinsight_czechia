
import pytest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# This import will fail initially (Red Phase)
try:
    from tools.location_normalizer import LocationNormalizer
except ImportError:
    LocationNormalizer = None

def test_normalize_prague():
    assert LocationNormalizer is not None, "LocationNormalizer not implemented"
    normalizer = LocationNormalizer()
    
    # Test variations of Prague
    test_cases = ["Praha", "Prague", "Praha 4", "Praha 10", "Prague, Czech Republic"]
    for case in test_cases:
        region, city = normalizer.normalize(case)
        assert region == "Prague"
        assert city == "Prague"

def test_normalize_brno():
    assert LocationNormalizer is not None, "LocationNormalizer not implemented"
    normalizer = LocationNormalizer()
    
    test_cases = ["Brno", "Brno-město", "Brno, CZ"]
    for case in test_cases:
        region, city = normalizer.normalize(case)
        assert region == "Brno"
        assert city == "Brno"

def test_normalize_ostrava():
    assert LocationNormalizer is not None, "LocationNormalizer not implemented"
    normalizer = LocationNormalizer()
    
    test_cases = ["Ostrava", "Ostrava-město", "Ostrava, Moravskoslezský kraj"]
    for case in test_cases:
        region, city = normalizer.normalize(case)
        assert region == "Ostrava"
        assert city == "Ostrava"

def test_normalize_other():
    assert LocationNormalizer is not None, "LocationNormalizer not implemented"
    normalizer = LocationNormalizer()
    
    # Other locations should be mapped to "Other" or kept as is
    region, city = normalizer.normalize("Plzeň")
    assert region == "Other"
    assert city == "Plzeň"
