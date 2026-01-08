
import pandas as pd
import numpy as np

class RegionalAnalysis:
    """Calculates granular regional insights for the job market."""
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize with job data.
        
        Args:
            df: DataFrame containing normalized 'region' and 'avg_salary' columns.
        """
        self.df = df

    def get_regional_stats(self) -> pd.DataFrame:
        """
        Calculates median salary and job count for each hub.
        
        Returns:
            DataFrame with columns: Region, Median Salary, Job Count.
        """
        if self.df.empty or 'region' not in self.df.columns:
            return pd.DataFrame(columns=['Region', 'Median Salary', 'Job Count'])
            
        # Target regions
        hubs = ["Prague", "Brno", "Ostrava"]
        
        results = []
        for region in hubs:
            region_df = self.df[self.df['region'] == region]
            count = len(region_df)
            
            # Median salary from valid entries
            valid_salaries = region_df[region_df['avg_salary'] > 0]['avg_salary']
            median = valid_salaries.median() if not valid_salaries.empty else 0
            
            results.append({
                "Region": region,
                "Median Salary": int(median) if not pd.isna(median) else 0,
                "Job Count": count
            })
            
        return pd.DataFrame(results)
