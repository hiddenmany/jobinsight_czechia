"""
Trends Analysis Module

Extracted from MarketIntelligence for emerging trends, ghost job detection,
and market signal analysis.
"""

import pandas as pd
import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TrendsAnalysis:
    """Trend detection and market signal analytics."""
    
    def __init__(self, df: pd.DataFrame, taxonomy: dict):
        """
        Initialize with data and taxonomy.
        
        Args:
            df: DataFrame with job data
            taxonomy: Loaded taxonomy dict with skill_patterns, toxicity, etc.
        """
        self.df = df
        self.taxonomy = taxonomy
    
    def get_emerging_tech_signals(self) -> pd.DataFrame:
        """Detect hot/emerging technologies based on mention frequency."""
        skill_patterns = self.taxonomy.get('skill_patterns', {})
        
        emerging_techs = ['Rust', 'Go', 'AI/ML', 'GraphQL', 'Terraform', 
                         'dbt', 'Kafka', 'Snowflake', 'Databricks']

        results = []
        for tech in emerging_techs:
            if tech not in skill_patterns:
                continue
            
            pattern = skill_patterns[tech]
            try:
                mask = self.df['description'].fillna('').str.lower().str.contains(
                    pattern, regex=True, case=False, na=False
                )
                count = mask.sum()
                if count >= 5:
                    results.append({
                        'Technology': tech,
                        'Mentions': int(count),
                        'Percentage': f"{(count / len(self.df) * 100):.1f}%"
                    })
            except Exception as e:
                logger.debug(f"Pattern failed for {tech}: {e}")
                continue

        if not results:
            return pd.DataFrame(columns=['Technology', 'Mentions', 'Percentage'])

        return pd.DataFrame(results).sort_values('Mentions', ascending=False)

    def get_new_market_entrants(self) -> pd.DataFrame:
        """Identify companies with moderate posting volume (potential growing startups)."""
        if self.df.empty:
            return pd.DataFrame(columns=['Company', 'Job Count', 'Status'])

        company_counts = self.df['company'].value_counts()
        
        # 5-15 postings indicates growing company, not yet a major employer
        entrants = company_counts[(company_counts >= 5) & (company_counts <= 15)]
        
        result = entrants.reset_index()
        result.columns = ['Company', 'Job Count']
        result['Status'] = 'Growing'
        
        return result.head(10)

    def get_ghost_jobs(self) -> pd.DataFrame:
        """Detect jobs with high ghost score indicating potentially fake listings."""
        if 'ghost_score' not in self.df.columns:
            return pd.DataFrame(columns=['Title', 'Company', 'Ghost Score'])

        suspicious = self.df[self.df['ghost_score'] >= 50].copy()
        
        if suspicious.empty:
            return pd.DataFrame(columns=['Title', 'Company', 'Ghost Score'])

        return suspicious[['title', 'company', 'ghost_score']].sort_values(
            'ghost_score', ascending=False
        ).head(20).rename(columns={
            'title': 'Title',
            'company': 'Company', 
            'ghost_score': 'Ghost Score'
        })

    def get_ai_washing_nontech(self) -> pd.DataFrame:
        """Detect non-tech companies using AI buzzwords without substance."""
        ai_buzzwords = ['ai', 'machine learning', 'artificial intelligence', 'ml', 
                        'deep learning', 'neural network', 'chatgpt', 'llm']
        
        pattern = '|'.join([re.escape(w) for w in ai_buzzwords])
        
        desc = self.df['description'].fillna('').str.lower()
        has_ai_buzz = desc.str.contains(pattern, regex=True, na=False)
        
        # Non-tech: roles that aren't Software/Data/DevOps
        tech_roles = ['Software', 'Data', 'DevOps', 'Engineering', 'Tech']
        is_non_tech = ~self.df['role_type'].isin(tech_roles)
        
        ai_washing = self.df[has_ai_buzz & is_non_tech].copy()
        
        if ai_washing.empty:
            return pd.DataFrame(columns=['Company', 'Role', 'AI Mentions'])

        return ai_washing.groupby('company').size().reset_index(
            name='AI Mentions'
        ).sort_values('AI Mentions', ascending=False).head(10)

    def get_toxicity_flags(self) -> pd.DataFrame:
        """Identify jobs with high toxicity scores."""
        if 'toxicity_score' not in self.df.columns:
            return pd.DataFrame(columns=['Title', 'Company', 'Toxicity Score'])

        toxic = self.df[self.df['toxicity_score'] >= 30].copy()
        
        if toxic.empty:
            return pd.DataFrame(columns=['Title', 'Company', 'Toxicity Score'])

        return toxic[['title', 'company', 'toxicity_score']].sort_values(
            'toxicity_score', ascending=False
        ).head(15).rename(columns={
            'title': 'Title',
            'company': 'Company',
            'toxicity_score': 'Toxicity Score'
        })
