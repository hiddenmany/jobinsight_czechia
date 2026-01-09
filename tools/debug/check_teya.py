import sqlite3
import os

db_path = r'C:\Users\phone\Desktop\JobsCzInsight\data\jobs.db'

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
print(f"Tables: {tables}")

# Guessing 'jobs' table based on common patterns
for table in tables:
    try:
        cursor.execute(f"SELECT title, company, category, description FROM {table} WHERE company LIKE '%Teya%' OR company LIKE '%Storyous%';")
        rows = cursor.fetchall()
        if rows:
            print(f"Found {len(rows)} matching records in table '{table}':")
            for row in rows:
                print(f"TITLE: {row[0]}")
                print(f"COMPANY: {row[1]}")
                print(f"CATEGORY: {row[2]}")
                print(f"DESCRIPTION: {row[3][:200]}...") # Truncated description
                print("-" * 20)
    except sqlite3.OperationalError:
        continue

conn.close()
