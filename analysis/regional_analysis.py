
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

    def get_regional_trends(self) -> pd.DataFrame:
        """
        Calculates median salary change for each hub between two most recent dates.
        
        Returns:
            DataFrame with columns: Region, Previous Median, Current Median, Change %.
        """
        if self.df.empty or 'scraped_at' not in self.df.columns or 'region' not in self.df.columns:
            return pd.DataFrame(columns=['Region', 'Previous Median', 'Current Median', 'Change %'])

        # Ensure datetime and get dates
        df = self.df.copy()
        df['date'] = pd.to_datetime(df['scraped_at']).dt.date
        dates = sorted(df['date'].unique(), reverse=True)

        if len(dates) < 2:
            return pd.DataFrame(columns=['Region', 'Previous Median', 'Current Median', 'Change %'])

        current_date = dates[0]
        previous_date = dates[1]

        hubs = ["Prague", "Brno", "Ostrava"]
        results = []

        for region in hubs:
            # Current Median
            curr_df = df[(df['region'] == region) & (df['date'] == current_date) & (df['avg_salary'] > 0)]
            curr_median = curr_df['avg_salary'].median() if not curr_df.empty else 0

            # Previous Median
            prev_df = df[(df['region'] == region) & (df['date'] == previous_date) & (df['avg_salary'] > 0)]
            prev_median = prev_df['avg_salary'].median() if not prev_df.empty else 0

            # Calculate change
            change_pct = 0
            if prev_median > 0 and curr_median > 0:
                change_pct = ((curr_median / prev_median) - 1) * 100

            results.append({
                "Region": region,
                "Previous Median": int(prev_median) if not pd.isna(prev_median) else 0,
                "Current Median": int(curr_median) if not pd.isna(curr_median) else 0,
                "Change %": round(float(change_pct), 1)
            })

        return pd.DataFrame(results)
