import os
import datetime
import duckdb
from settings import settings

def get_stats():
    """Fetch key statistics from the database."""
    db_path = str(settings.get_db_path())
    if not os.path.exists(db_path):
        return None

    try:
        con = duckdb.connect(db_path, read_only=True)
        
        # Total active jobs
        total_jobs = con.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
        
        # 1. Professional Market Median (Tech/White-collar focus)
        prof_roles = (
            'Developer', 'Analyst', 'Management', 'PM', 'Sales', 'HR', 
            'Marketing', 'Designer', 'QA', 'Finance', 'Legal', 
            'Education', 'Technical Specialists', 'Electromechanics'
        )
        roles_sql = ", ".join([f"'{r}'" for r in prof_roles])
        
        prof_median = con.execute(f"""
            SELECT MEDIAN(avg_salary) 
            FROM signals 
            WHERE avg_salary > 0 
            AND role_type IN ({roles_sql})
        """).fetchone()[0]

        # 2. National Equivalent Median (All Roles, HPP Only - approximates ČSÚ methodology)
        # Exclude IČO (Contractor) and Brigáda (Part-time) keywords
        # This is a rough SQL filter to mimic the Python logic
        hpp_median = con.execute("""
            SELECT MEDIAN(avg_salary) 
            FROM signals 
            WHERE avg_salary > 0 
            AND lower(description) NOT LIKE '%ico%' 
            AND lower(description) NOT LIKE '%faktur%' 
            AND lower(description) NOT LIKE '%živnost%' 
            AND lower(description) NOT LIKE '%osvč%'
            AND lower(description) NOT LIKE '%dpp%' 
            AND lower(description) NOT LIKE '%dpč%' 
            AND lower(description) NOT LIKE '%brigád%' 
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
            "prof_median": int(prof_median) if prof_median else 0,
            "hpp_median": int(hpp_median) if hpp_median else 0,
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
    prof_salary_fmt = f"{stats['prof_median']:,}".replace(",", " ")
    hpp_salary_fmt = f"{stats['hpp_median']:,}".replace(",", " ")
    
    stats_content = f"""
### 📊 Current Market Pulse (Auto-Updated)
| Metric | Value | Context |
|--------|-------|---------|
| **Active Job Listings** | `{stats['total_jobs']:,}` | Across major Czech portals |
| **Professional Median** | `{prof_salary_fmt} CZK` | Tech, Management, & White-collar roles |
| **National Est. Median** | `{hpp_salary_fmt} CZK` | All roles, Full-time (HPP only) |
| **Top 3 Roles** | {stats['top_roles'][0][0]}, {stats['top_roles'][1][0]}, {stats['top_roles'][2][0]} | High volume demand |
| **Last Updated** | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M UTC')} | |

> *Note: 'National Est. Median' approximates ČSÚ methodology (HPP only), while 'Professional Median' reflects the target audience of this report.*
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
