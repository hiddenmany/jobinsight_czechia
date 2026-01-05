import os
import datetime
import duckdb

def get_stats():
    """Fetch key statistics from the database."""
    db_path = os.path.join("data", "intelligence.db")
    if not os.path.exists(db_path):
        return None

    try:
        con = duckdb.connect(db_path, read_only=True)
        
        # Total active jobs
        total_jobs = con.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
        
        # Median Salary (non-zero)
        median_salary = con.execute("""
            SELECT MEDIAN(avg_salary) 
            FROM signals 
            WHERE avg_salary > 0
        """).fetchone()[0]
        
        # Top 5 Roles
        top_roles = con.execute("""
            SELECT role_type, COUNT(*) as count 
            FROM signals 
            GROUP BY role_type 
            ORDER BY count DESC 
            LIMIT 5
        """).fetchall()
        
        # Last scrape date
        last_date = con.execute("SELECT MAX(scraped_at) FROM signals").fetchone()[0]
        
        con.close()
        
        return {
            "total_jobs": total_jobs,
            "median_salary": int(median_salary) if median_salary else 0,
            "top_roles": top_roles,
            "last_date": last_date
        }
    except Exception as e:
        print(f"Error reading database: {e}")
        return None

def update_readme():
    stats = get_stats()
    if not stats:
        print("No stats available to update.")
        return

    readme_path = "README.md"
    if not os.path.exists(readme_path):
        print("README.md not found.")
        return

    # Format the stats block
    roles_str = ", ".join([f"{r[0]} ({r[1]})" for r in stats['top_roles']])
    salary_fmt = f"{stats['median_salary']:,}".replace(",", " ")
    
    stats_content = f"""
### 📊 Current Market Pulse (Auto-Updated)
| Metric | Value |
|--------|-------|
| **Active Job Listings** | `{stats['total_jobs']:,}` |
| **Median Advertised Salary** | `{salary_fmt} CZK` |
| **Top 3 Roles** | {stats['top_roles'][0][0]}, {stats['top_roles'][1][0]}, {stats['top_roles'][2][0]} |
| **Last Updated** | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M UTC')} |

> *Based on real-time analysis of {stats['total_jobs']:,} job postings from major Czech portals.*
"""

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    start_marker = "<!-- START_STATS -->"
    end_marker = "<!-- END_STATS -->"

    if start_marker not in content or end_marker not in content:
        print("Markers not found in README.md")
        return

    pre_content = content.split(start_marker)[0]
    post_content = content.split(end_marker)[1]

    new_content = f"{pre_content}{start_marker}\n{stats_content}\n{end_marker}{post_content}"

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print("README.md updated with latest stats.")

if __name__ == "__main__":
    update_readme()
