import pandas as pd
import analyzer

# Load Data
print("Loading data...")
intel = analyzer.MarketIntelligence()
df = intel.df
print(f"Total Rows in DF: {len(df)}")

# Simulate default filtering
filtered_df = df.copy()
print(f"Rows after filtering (All/All): {len(filtered_df)}")

if not filtered_df.empty:
    # Aggregate data by company
    company_stats = filtered_df.groupby('company').agg(
        volume=('title', 'count'),
        avg_salary=('avg_salary', 'median'),
        source=('source', 'first')
    ).reset_index()
    
    print(f"Company Stats Rows: {len(company_stats)}")
    
    # Check for valid salary data
    valid_salary_stats = company_stats[company_stats['avg_salary'] > 0]
    print(f"Company Stats with Salary > 0: {len(valid_salary_stats)}")
    
    if len(valid_salary_stats) == 0:
        print("CRITICAL: No companies have valid median salary data.")
    else:
        print(valid_salary_stats.head())
else:
    print("Filtered DF is empty.")
