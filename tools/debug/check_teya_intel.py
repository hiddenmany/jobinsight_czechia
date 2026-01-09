import sqlite3
import os

db_path = r'C:\Users\phone\Desktop\JobsCzInsight\data\intelligence.db'

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
print(f"Tables: {tables}")

for table in tables:
    try:
        cursor.execute(f"SELECT * FROM {table} LIMIT 1;")
        cols = [description[0] for description in cursor.description]
        
        query = f"SELECT * FROM {table} WHERE "
        query += " OR ".join([f"{col} LIKE '%Teya%' OR {col} LIKE '%Storyous%'" for col in cols if "id" not in col.lower()])
        
        cursor.execute(query)
        rows = cursor.fetchall()
        if rows:
            print(f"Found {len(rows)} matching records in table '{table}':")
            for row in rows:
                # Map row to column names for readability
                record = dict(zip(cols, row))
                print(f"TITLE: {record.get('title', record.get('role_type', 'N/A'))}")
                print(f"COMPANY: {record.get('company', 'N/A')}")
                print(f"CITY: {record.get('city', 'N/A')}")
                print(f"DESCRIPTION: {str(record.get('description', 'N/A'))[:200]}...")
                print("-" * 20)
    except sqlite3.OperationalError as e:
        print(f"Error querying {table}: {e}")
        continue

conn.close()
