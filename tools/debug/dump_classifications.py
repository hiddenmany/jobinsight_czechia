import duckdb

db_path = r'C:\Users\phone\Desktop\JobsCzInsight\data\intelligence.db'
con = duckdb.connect(db_path)

# query for distinct title and role_type
query = """
    SELECT DISTINCT role_type, title 
    FROM signals 
    ORDER BY role_type, title
"""

results = con.execute(query).fetchall()

output_path = r'current_classifications.txt'
with open(output_path, 'w', encoding='utf-8') as f:
    current_role = None
    for role, title in results:
        if role != current_role:
            f.write(f"\n--- {role} ---\n")
            current_role = role
        f.write(f"{title}\n")

print(f"Exported {len(results)} distinct classifications to {output_path}")
