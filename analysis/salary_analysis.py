"""
Salary Analysis Module

Extracted from MarketIntelligence for focused salary-related analytics.
"""

import pandas as pd
import numpy as np
import re
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class SalaryAnalysis:
    """Salary-focused analytics for job market data."""
    
    def __init__(self, df: pd.DataFrame, taxonomy: dict):
        """
        Initialize with data and taxonomy.
        
        Args:
            df: DataFrame with job data (must have 'avg_salary', 'role_type', etc.)
            taxonomy: Loaded taxonomy dict with skill_patterns, etc.
        """
        self.df = df
        self.taxonomy = taxonomy
    
    def get_salary_by_role(self) -> pd.DataFrame:
        """Get median salary breakdown by role type."""
        valid_sal = self.df[self.df['avg_salary'] > 0]
        result = valid_sal.groupby('role_type').agg(
            median_salary=('avg_salary', 'median'),
            count=('avg_salary', 'count')
        ).sort_values('median_salary', ascending=False).reset_index()
        return result[result['count'] >= 1]
    
    def get_salary_by_seniority(self) -> pd.DataFrame:
        """Get median salary breakdown by seniority level."""
        valid_sal = self.df[self.df['avg_salary'] > 0]
        result = valid_sal.groupby('seniority_level').agg(
            median_salary=('avg_salary', 'median'),
            count=('avg_salary', 'count')
        ).reset_index()
        order = ['Junior', 'Mid', 'Senior', 'Lead', 'Executive']
        result['order'] = result['seniority_level'].apply(lambda x: order.index(x) if x in order else 99)
        return result.sort_values('order').drop('order', axis=1)

    def get_salary_by_contract_type(self) -> Dict[str, float]:
        """Get median salary for HPP vs Brigáda."""
        valid_sal = self.df[self.df['avg_salary'] > 0]
        result = valid_sal.groupby('contract_type')['avg_salary'].median()
        return result.to_dict()

    def get_seniority_role_matrix(self) -> pd.DataFrame:
        """Cross-analysis: Median salary by Seniority + Role."""
        valid_sal = self.df[self.df['avg_salary'] > 0]
        top_roles = valid_sal['role_type'].value_counts().head(6).index
        filtered = valid_sal[valid_sal['role_type'].isin(top_roles)]
        
        matrix = filtered.groupby(['seniority_level', 'role_type']).agg(
            median_salary=('avg_salary', 'median'),
            count=('avg_salary', 'count')
        ).reset_index()
        matrix = matrix[matrix['count'] >= 3]
        return matrix.sort_values(['role_type', 'median_salary'], ascending=[True, False])

    def get_salary_by_city(self) -> pd.DataFrame:
        """Get median salary breakdown by city/location."""
        valid_sal = self.df[self.df['avg_salary'] > 0]
        if 'city' not in valid_sal.columns:
            return pd.DataFrame(columns=['city', 'median_salary', 'count'])
        
        result = valid_sal.groupby('city').agg(
            median_salary=('avg_salary', 'median'),
            count=('avg_salary', 'count')
        ).reset_index()
        return result[result['count'] >= 5].sort_values('median_salary', ascending=False)

    def get_salary_trend_weekly(self) -> pd.DataFrame:
        """Get weekly median salary trends (requires 7+ days of data)."""
        df_with_dates = self.df.copy()
        df_with_dates['scraped_date'] = pd.to_datetime(df_with_dates['scraped_at']).dt.date
        
        if df_with_dates['scraped_date'].nunique() < 7:
            return pd.DataFrame(columns=['week', 'median_salary', 'count'])

        valid_sal = df_with_dates[df_with_dates['avg_salary'] > 0]
        valid_sal['week'] = pd.to_datetime(valid_sal['scraped_at']).dt.to_period('W')

        trend = valid_sal.groupby('week').agg(
            median_salary=('avg_salary', 'median'),
            count=('avg_salary', 'count')
        ).reset_index()
        trend['week'] = trend['week'].astype(str)
        return trend

    def get_remote_salary_premium(self) -> Dict[str, Any]:
        """Calculate salary premium for remote vs office jobs."""
        work_model_kw = self.taxonomy.get('work_model_keywords', {})
        remote_pattern = '|'.join(work_model_kw.get('remote', []))

        valid_sal = self.df[self.df['avg_salary'] > 0]
        desc = valid_sal['description'].fillna('').str.lower()
        is_remote = desc.str.contains(remote_pattern, case=False, na=False, regex=True)

        remote_median = valid_sal[is_remote]['avg_salary'].median()
        office_median = valid_sal[~is_remote]['avg_salary'].median()

        if pd.notna(remote_median) and pd.notna(office_median) and office_median > 0:
            premium_pct = int(((remote_median / office_median) - 1) * 100)
            return {
                'remote_median': int(remote_median),
                'office_median': int(office_median),
                'premium': f"+{premium_pct}%" if premium_pct >= 0 else f"{premium_pct}%",
                'premium_raw': premium_pct
            }
        return {'remote_median': 0, 'office_median': 0, 'premium': 'N/A', 'premium_raw': 0}

    def get_skill_premiums(self) -> pd.DataFrame:
        """Calculate salary premium for top skills using taxonomy patterns."""
        skill_patterns = self.taxonomy.get('skill_patterns', {})
        priority_skills = ['Python', 'JavaScript', 'TypeScript', 'Java', 'Go', 'Rust',
                          'React', 'Angular', 'Vue', 'Node.js', '.NET', 'Spring',
                          'SQL', 'MongoDB', 'Redis', 'Docker', 'Kubernetes',
                          'AWS', 'Azure', 'GCP', 'AI/ML']

        valid_sal = self.df[self.df['avg_salary'] > 0]
        if valid_sal.empty:
            return pd.DataFrame(columns=['Skill', 'Median', 'Premium', 'Jobs'])

        baseline_median = valid_sal['avg_salary'].median()
        premiums = []

        for skill_name in priority_skills:
            if skill_name not in skill_patterns:
                continue

            pattern = skill_patterns[skill_name]
            try:
                mask = valid_sal['description'].fillna('').str.lower().str.contains(
                    pattern, regex=True, case=False, na=False
                )
                skill_median = valid_sal[mask]['avg_salary'].median()
                count = mask.sum()

                if pd.notna(skill_median) and count >= 10:
                    premium_pct = ((skill_median / baseline_median) - 1) * 100
                    premiums.append({
                        'Skill': skill_name,
                        'Median': int(skill_median),
                        'Premium': f"+{int(premium_pct)}%" if premium_pct >= 0 else f"{int(premium_pct)}%",
                        'Premium_Raw': premium_pct,
                        'Jobs': int(count)
                    })
            except Exception as e:
                logger.debug(f"Regex failed for {skill_name}, using fallback: {e}")
                mask = valid_sal['description'].fillna('').str.lower().str.contains(
                    skill_name.lower(), regex=False
                )
                skill_median = valid_sal[mask]['avg_salary'].median()
                count = mask.sum()
                if pd.notna(skill_median) and count >= 10:
                    premium_pct = ((skill_median / baseline_median) - 1) * 100
                    premiums.append({
                        'Skill': skill_name,
                        'Median': int(skill_median),
                        'Premium': f"+{int(premium_pct)}%" if premium_pct >= 0 else f"{int(premium_pct)}%",
                        'Premium_Raw': premium_pct,
                        'Jobs': int(count)
                    })

        if not premiums:
            return pd.DataFrame(columns=['Skill', 'Median', 'Premium', 'Jobs'])

        return pd.DataFrame(premiums).sort_values('Premium_Raw', ascending=False).drop('Premium_Raw', axis=1)
