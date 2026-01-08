
import pytest
import pandas as pd
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# This import will fail initially (Red Phase)
try:
    from analysis.regional_analysis import RegionalAnalysis
except ImportError:
    RegionalAnalysis = None

def test_regional_stats_calculation():
    assert RegionalAnalysis is not None, "RegionalAnalysis not implemented"
    
    # Create mock data
    data = [
        {"region": "Prague", "avg_salary": 100000},
        {"region": "Prague", "avg_salary": 80000},
        {"region": "Brno", "avg_salary": 70000},
        {"region": "Ostrava", "avg_salary": 60000},
        {"region": "Other", "avg_salary": 50000},
        {"region": "Prague", "avg_salary": 0}, # Invalid salary should be ignored
    ]
    df = pd.DataFrame(data)
    
    analyzer = RegionalAnalysis(df)
    stats = analyzer.get_regional_stats()
    
    # Verify Prague
    prague = stats[stats['Region'] == 'Prague'].iloc[0]
    assert prague['Median Salary'] == 90000 # median of [100k, 80k]
    assert prague['Job Count'] == 3 # All jobs in Prague
    
    # Verify Brno
    brno = stats[stats['Region'] == 'Brno'].iloc[0]
    assert brno['Median Salary'] == 70000
    assert brno['Job Count'] == 1
