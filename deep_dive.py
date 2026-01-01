import pandas as pd
import analyzer
import re
from collections import Counter

# Load Data
intel = analyzer.MarketIntelligence()
df = intel.df

print(f"--- DATA DEEP DIVE REPORT ---")
print(f"Total Rows: {len(df)}")
print(f"Data Sources: {df['source'].unique()}")

# 1. THE PLATFORM PREMIUM (Where is the money?)
if 'avg_salary' in df.columns:
    print("\n[1] PLATFORM SALARY PREMIUM (Median CZK):")
    platform_stats = df[df['avg_salary'] > 0].groupby('source')['avg_salary'].median().sort_values(ascending=False)
    print(platform_stats)

# 2. TRANSPARENCY TAX (Do transparent ads pay more?)
print("\n[2] THE TRANSPARENCY PARADOX:")
transparent_pay = df[df['avg_salary'] > 0]['avg_salary'].median()
# We don't have non-transparent salary data (obviously), but we can check if 
# companies with HIGH transparency (across their ads) pay differently than those with LOW transparency.
# Calculate company transparency score
company_transparency = df.groupby('company').apply(lambda x: (x['avg_salary'].gt(0).sum() / len(x)) * 100)
high_transparency_companies = company_transparency[company_transparency > 80].index
low_transparency_companies = company_transparency[company_transparency < 20].index

pay_high_transp = df[(df['company'].isin(high_transparency_companies)) & (df['avg_salary'] > 0)]['avg_salary'].median()
pay_low_transp = df[(df['company'].isin(low_transparency_companies)) & (df['avg_salary'] > 0)]['avg_salary'].median()

print(f"Median Pay @ High Transparency Companies (>80% ads with salary): {pay_high_transp:,.0f} CZK")
print(f"Median Pay @ Low Transparency Companies (<20% ads with salary): {pay_low_transp:,.0f} CZK")

# 3. KEYWORD VALUATION (What words print money?)
print("\n[3] KEYWORD VALUE (Correlation with Salary):")
keywords = ['senior', 'junior', 'remote', 'english', 'angličtina', 'python', 'sales', 'praha', 'benefit', 'flexibil']
keyword_stats = {}

for kw in keywords:
    # Filter rows containing keyword in title or description
    mask = df['title'].str.contains(kw, case=False, na=False) | df['description'].str.contains(kw, case=False, na=False)
    matches = df[mask & (df['avg_salary'] > 0)]
    if len(matches) > 10:
        keyword_stats[kw] = matches['avg_salary'].median()

# Sort by value
sorted_kws = sorted(keyword_stats.items(), key=lambda x: x[1], reverse=True)
for k, v in sorted_kws:
    print(f"'{k}': {v:,.0f} CZK (n={len(df[df['title'].str.contains(k, case=False, na=False)])})")

# 4. iSTYLE CONTEXT
print("\n[4] iSTYLE POSITIONING:")
istyle_ads = df[df['company'].str.contains('iSTYLE', case=False, na=False)]
if not istyle_ads.empty:
    print(f"iSTYLE Ads Found: {len(istyle_ads)}")
    if istyle_ads['avg_salary'].sum() > 0:
         print(f"iSTYLE Median: {istyle_ads[istyle_ads['avg_salary'] > 0]['avg_salary'].median():,.0f} CZK")
    else:
         print("iSTYLE has NO visible salaries.")
else:
    print("No iSTYLE ads found.")
