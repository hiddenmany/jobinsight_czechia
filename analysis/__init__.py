"""
JobsCzInsight Analysis Package

Focused modules for market intelligence analysis, extracted from the
original monolithic MarketIntelligence class for maintainability.

Usage:
    from analysis import SalaryAnalysis, BenefitsAnalysis, LocationAnalysis, TrendsAnalysis
    
    # Or via the facade for backward compatibility:
    from analyzer import MarketIntelligence
"""

from analysis.salary_analysis import SalaryAnalysis
from analysis.benefits_analysis import BenefitsAnalysis
from analysis.location_analysis import LocationAnalysis
from analysis.trends_analysis import TrendsAnalysis

__all__ = ['SalaryAnalysis', 'BenefitsAnalysis', 'LocationAnalysis', 'TrendsAnalysis']
