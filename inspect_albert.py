import duckdb
import pandas as pd
import os

# Connect to DB (read-only)
con = duckdb.connect("data/intelligence.db", read_only=True)

# 1. Find exact company names matching "Albert"
print("--- Searching for company names matching 'Albert' ---")
companies = con.execute("SELECT DISTINCT company FROM signals WHERE company ILIKE '%Albert%'" ).fetchall()
for c in companies:
    print(f"Found: {c[0]}")

# 2. Analyze Albert's jobs
print("\n--- Albert Job Analysis ---")
query = """
    SELECT 
        title, 
        role_type, 
        tech_status, 
        description
    FROM signals 
    WHERE company ILIKE '%Albert%'
"""
df = con.execute(query).df()

if df.empty:
    print("No jobs found for Albert.")
else:
    print(f"Total Jobs: {len(df)}")
    
    print("\nRole Distribution:")
    print(df['role_type'].value_counts())
    
    print("\nTech Status Distribution:")
    print(df['tech_status'].value_counts())
    
    print("\n--- Sample 'Modern' Jobs from Albert ---")
    modern_jobs = df[df['tech_status'] == 'Modern']
    if not modern_jobs.empty:
        for idx, row in modern_jobs.head(10).iterrows():
            print(f"- {row['title']} ({row['role_type']})")
    else:
        print("No 'Modern' jobs found.")

    print("\n--- 'Agile' keyword check in Modern jobs ---")
    # Check if 'agile' or 'scrum' is the driver
    agile_count = 0
    for desc in modern_jobs['description']:
        if desc and ('agile' in desc.lower() or 'scrum' in desc.lower()):
            agile_count += 1
    print(f"Modern jobs mentioning Agile/Scrum: {agile_count} / {len(modern_jobs)}")
