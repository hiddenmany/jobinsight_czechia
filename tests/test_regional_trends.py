
import pytest
import pandas as pd
from datetime import datetime, timedelta
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.regional_analysis import RegionalAnalysis

def test_regional_trends_calculation():
    # Create mock data for two different dates
    today = datetime.now().date()
    last_week = today - timedelta(days=7)
    
    data = [
        # Last week
        {"region": "Prague", "avg_salary": 80000, "scraped_at": pd.Timestamp(last_week)},
        {"region": "Brno", "avg_salary": 70000, "scraped_at": pd.Timestamp(last_week)},
        # Today
        {"region": "Prague", "avg_salary": 88000, "scraped_at": pd.Timestamp(today)}, # +10%
        {"region": "Brno", "avg_salary": 63000, "scraped_at": pd.Timestamp(today)}, # -10%
    ]
    df = pd.DataFrame(data)
    
    analyzer = RegionalAnalysis(df)
    trends = analyzer.get_regional_trends()
    
    # Verify Prague trend
    prague = trends[trends['Region'] == 'Prague'].iloc[0]
    assert prague['Previous Median'] == 80000
    assert prague['Current Median'] == 88000
    assert prague['Change %'] == 10.0
    
    # Verify Brno trend
    brno = trends[trends['Region'] == 'Brno'].iloc[0]
    assert brno['Change %'] == -10.0
