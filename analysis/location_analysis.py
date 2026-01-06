"""
Location Analysis Module

Extracted from MarketIntelligence for focused location and work model analytics.
"""

import pandas as pd
import numpy as np
import re
from typing import Dict, List


class LocationAnalysis:
    """Location and work model analytics for job market data."""
    
    def __init__(self, df: pd.DataFrame, taxonomy: dict):
        """
        Initialize with data and taxonomy.
        
        Args:
            df: DataFrame with job data
            taxonomy: Loaded taxonomy dict with work_model_keywords
        """
        self.df = df
        self.taxonomy = taxonomy
    
    def get_location_distribution(self) -> pd.DataFrame:
        """Get job distribution by location."""
        if 'city' not in self.df.columns:
            return pd.DataFrame(columns=['city', 'count'])
        return self.df['city'].value_counts().reset_index().head(15)

    def get_work_model_distribution(self) -> pd.DataFrame:
        """Classify jobs by work model: Remote, Hybrid, Office."""
        work_model_kw = self.taxonomy.get('work_model_keywords', {})
        
        remote_pattern = '|'.join(work_model_kw.get('remote', []))
        hybrid_pattern = '|'.join(work_model_kw.get('hybrid', []))

        desc = self.df['description'].fillna('').str.lower()

        conditions = [
            desc.str.contains(remote_pattern, case=False, na=False, regex=True),
            desc.str.contains(hybrid_pattern, case=False, na=False, regex=True)
        ]
        choices = ['Remote', 'Hybrid']
        
        self.df['work_model'] = np.select(conditions, choices, default='Office')
        
        result = self.df['work_model'].value_counts().reset_index()
        result.columns = ['Work Model', 'Count']
        return result

    def get_work_model_by_role(self) -> pd.DataFrame:
        """Show work model distribution for top roles."""
        if self.df.empty:
            return pd.DataFrame(columns=['Role', 'Remote %', 'Hybrid %', 'Office %'])

        work_model_kw = self.taxonomy.get('work_model_keywords', {})
        remote_pattern = '|'.join(work_model_kw.get('remote', []))
        hybrid_pattern = '|'.join(work_model_kw.get('hybrid', []))

        def classify_work_model(desc_text: str) -> str:
            if pd.isna(desc_text):
                return 'Office'
            desc_lower = desc_text.lower()
            if re.search(remote_pattern, desc_lower):
                return 'Remote'
            if re.search(hybrid_pattern, desc_lower):
                return 'Hybrid'
            return 'Office'

        df_copy = self.df.copy()
        df_copy['work_model_temp'] = df_copy['description'].apply(classify_work_model)

        top_roles = df_copy['role_type'].value_counts().head(8).index
        filtered = df_copy[df_copy['role_type'].isin(top_roles)]

        result = filtered.groupby(['role_type', 'work_model_temp']).size().unstack(fill_value=0)
        result = result.div(result.sum(axis=1), axis=0) * 100
        result = result.round(1).reset_index()

        return result
