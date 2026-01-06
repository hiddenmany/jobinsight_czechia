"""
Benefits Analysis Module

Extracted from MarketIntelligence for focused benefits-related analytics.
"""

import pandas as pd
import re
from typing import Dict, List

# Import shared constant
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analyzer import BENEFIT_DISPLAY_NAMES


class BenefitsAnalysis:
    """Benefits-focused analytics for job market data."""
    
    def __init__(self, df: pd.DataFrame, taxonomy: dict):
        """
        Initialize with data and taxonomy.
        
        Args:
            df: DataFrame with job data
            taxonomy: Loaded taxonomy dict with benefits_keywords
        """
        self.df = df
        self.taxonomy = taxonomy
    
    def get_benefits_analysis(self) -> pd.DataFrame:
        """Analyze which benefits are most commonly offered."""
        benefits_cats = self.taxonomy.get('benefits_keywords', {})

        results = []
        for benefit_name, keywords in benefits_cats.items():
            pattern = '|'.join([re.escape(kw) for kw in keywords])
            mask = self.df['description'].fillna('').str.lower().str.contains(
                pattern, regex=True, case=False
            )
            count = mask.sum()
            percentage = (count / len(self.df)) * 100

            if count > 0:
                display_name = BENEFIT_DISPLAY_NAMES.get(benefit_name, benefit_name.title())
                results.append({
                    'Benefit': display_name,
                    'Jobs': int(count),
                    'Percentage': f"{percentage:.1f}%",
                    'Percentage_Raw': percentage
                })

        if not results:
            return pd.DataFrame(columns=['Benefit', 'Jobs', 'Percentage'])

        return pd.DataFrame(results).sort_values(
            'Percentage_Raw', ascending=False
        ).drop('Percentage_Raw', axis=1)

    def get_benefits_by_role(self) -> pd.DataFrame:
        """Show which roles get the best benefits (top 3 benefits)."""
        if self.df.empty:
            return pd.DataFrame(columns=['Role', 'Benefit Count', 'Top Benefits'])

        benefits_cats = self.taxonomy.get('benefits_keywords', {})

        def count_benefits(desc: str) -> int:
            if pd.isna(desc):
                return 0
            desc_lower = desc.lower()
            count = 0
            for keywords in benefits_cats.values():
                pattern = '|'.join([re.escape(kw) for kw in keywords])
                if re.search(pattern, desc_lower):
                    count += 1
            return count

        df_copy = self.df.copy()
        df_copy['benefit_count'] = df_copy['description'].apply(count_benefits)

        role_benefits = df_copy.groupby('role_type').agg(
            avg_benefits=('benefit_count', 'mean'),
            job_count=('benefit_count', 'count')
        ).reset_index()

        role_benefits = role_benefits[role_benefits['job_count'] >= 10]
        return role_benefits.sort_values('avg_benefits', ascending=False).head(8)

    def get_trending_benefits(self) -> pd.DataFrame:
        """Show fastest-growing benefits (based on frequency)."""
        benefits_cats = self.taxonomy.get('benefits_keywords', {})

        results = []
        for benefit_name, keywords in benefits_cats.items():
            pattern = '|'.join([re.escape(kw) for kw in keywords])
            mask = self.df['description'].fillna('').str.lower().str.contains(
                pattern, regex=True, case=False
            )
            count = mask.sum()
            percentage = (count / len(self.df)) * 100

            if count >= 100:  # Minimum threshold
                display_name = BENEFIT_DISPLAY_NAMES.get(benefit_name, benefit_name.title())
                results.append({
                    'Benefit': display_name,
                    'Adoption': f"{percentage:.1f}%",
                    'Jobs': int(count),
                    'Adoption_Raw': percentage
                })

        if not results:
            return pd.DataFrame(columns=['Benefit', 'Adoption', 'Jobs'])

        return pd.DataFrame(results).sort_values(
            'Adoption_Raw', ascending=False
        ).drop('Adoption_Raw', axis=1).head(6)
