import duckdb
import json
import os
import yaml
from datetime import datetime

# Configuration
DB_PATH = 'data/intelligence.db'
OUTPUT_HTML = 'public/trends.html'
TAXONOMY_PATH = 'config/taxonomy.yaml'

# Load skill patterns from taxonomy
def load_skill_patterns():
    """Load skill detection patterns from taxonomy.yaml"""
    with open(TAXONOMY_PATH, 'r', encoding='utf-8') as f:
        taxonomy = yaml.safe_load(f)
    return taxonomy.get('skill_patterns', {})

SKILL_PATTERNS = load_skill_patterns()

def get_market_intelligence(conn):
    print("Generating Market Intelligence Data...")
    
    # 1. Salary Analysis by Role (Box Plot Approximation: Min, Avg, Max)
    # We filter out NULL salaries and suspiciously low values (< 20000 CZK)
    salary_query = """
        SELECT 
            role_type,
            COUNT(*) as job_count,
            MIN(avg_salary) as min_sal,
            AVG(avg_salary) as avg_sal,
            MAX(avg_salary) as max_sal
        FROM signals
        WHERE avg_salary > 20000 AND role_type IS NOT NULL
        GROUP BY role_type
        HAVING count(*) > 5
        ORDER BY avg_sal DESC
    """
    salary_results = conn.execute(salary_query).fetchall()
    
    salary_data = {
        "labels": [r[0] for r in salary_results],
        "datasets": [
            {"label": "Average Salary (CZK)", "data": [int(r[3]) for r in salary_results], "backgroundColor": "#36A2EB"},
            {"label": "Max Salary (CZK)", "data": [int(r[4]) for r in salary_results], "backgroundColor": "#FF6384", "hidden": True}
        ]
    }

    # 2. Top Hiring Companies (Overall)
    company_query = """
        SELECT company, COUNT(*) as count 
        FROM signals 
        WHERE company IS NOT NULL AND company != ''
        GROUP BY company 
        ORDER BY count DESC 
        LIMIT 15
    """
    top_companies = conn.execute(company_query).fetchall()
    
    # 3. "Hidden Tech" - Non-Tech companies hiring for Tech Roles
    # Refined Logic: Exclude retail/manual roles and require HARD tech skills using accurate patterns

    # Exclude common non-tech roles that might mention "PC skills" or "IT"
    exclude_roles = "('Sales', 'Retail', 'Driver', 'Warehouse', 'HR', 'Admin', 'Customer Service')"

    # Build tech filter using skill patterns - focus on core tech skills
    core_tech_skills = [
        'Python', 'Java', 'JavaScript', 'React', 'Angular', 'Vue',
        'Node.js', 'C#', '.NET', 'Go', 'Rust', 'Kotlin', 'Swift',
        'SQL', 'MongoDB', 'Redis', 'Docker', 'Kubernetes',
        'AWS', 'Azure', 'GCP', 'AI/ML', 'Data Science'
    ]

    # Use regex patterns for accurate detection
    tech_conditions = []
    for skill_name in core_tech_skills:
        if skill_name in SKILL_PATTERNS:
            pattern = SKILL_PATTERNS[skill_name]
            tech_conditions.append(f"regexp_matches(lower(description), '{pattern}')")

    tech_filter = " OR ".join(tech_conditions)

    tech_hiring_query = f"""
        SELECT company, COUNT(*) as tech_jobs
        FROM signals
        WHERE ({tech_filter})
        AND company IS NOT NULL
        AND role_type NOT IN {exclude_roles}
        AND lower(title) NOT LIKE '%prodavač%'
        AND lower(title) NOT LIKE '%skladník%'
        AND lower(title) NOT LIKE '%řidič%'
        AND lower(title) NOT LIKE '%asistent%'
        GROUP BY company
        ORDER BY tech_jobs DESC
        LIMIT 15
    """
    tech_hiring_companies = conn.execute(tech_hiring_query).fetchall()

    # 4. Skill Heatmap (Modern Stack) - Using accurate regex patterns
    skill_counts = []
    for skill_name, pattern in SKILL_PATTERNS.items():
        # Use regexp_matches for accurate detection with word boundaries
        query = f"SELECT COUNT(*) FROM signals WHERE regexp_matches(lower(description), '{pattern}')"
        try:
            count = conn.execute(query).fetchone()[0]
            skill_counts.append({"skill": skill_name, "count": count})
        except Exception as e:
            print(f"Error: Skill '{skill_name}' pattern failed: {e} - SKIPPING")
            continue  # Skip skills with invalid patterns instead of using loose matching

    # Filter out skills with very low counts (< 10 jobs) and sort
    skill_counts = [s for s in skill_counts if s['count'] >= 10]
    skill_counts.sort(key=lambda x: x['count'], reverse=True)

    # Limit to top 18 skills for readability
    skill_counts = skill_counts[:18]
    
    return {
        "salary": salary_data,
        "top_companies": {
            "labels": [r[0] for r in top_companies],
            "data": [r[1] for r in top_companies]
        },
        "tech_hiring": {
            "labels": [r[0] for r in tech_hiring_companies],
            "data": [r[1] for r in tech_hiring_companies]
        },
        "skills": {
            "labels": [x['skill'] for x in skill_counts],
            "data": [x['count'] for x in skill_counts]
        }
    }

def generate_executive_report(data):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>JobsCz Market Intelligence Report</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
        <style>
            :root {{ --primary: #2563eb; --secondary: #1e293b; --bg: #f8fafc; --card: #ffffff; }}
            body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--secondary); padding: 40px; margin: 0; }}
            .container {{ max-width: 1400px; margin: 0 auto; }}
            
            header {{ text-align: center; margin-bottom: 60px; }}
            h1 {{ font-weight: 800; font-size: 2.5rem; margin-bottom: 10px; color: #0f172a; }}
            .subtitle {{ color: #64748b; font-size: 1.1rem; }}
            
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(600px, 1fr)); gap: 30px; }}
            .card {{ background: var(--card); padding: 30px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border: 1px solid #e2e8f0; }}
            
            h2 {{ font-size: 1.25rem; font-weight: 600; margin-bottom: 25px; border-left: 5px solid var(--primary); padding-left: 15px; }}
            
            .insight-box {{ background: #eff6ff; padding: 15px; border-radius: 8px; margin-bottom: 20px; font-size: 0.9rem; color: #1e40af; }}
            
            canvas {{ max-height: 400px; width: 100%; }}
            
            .nav {{ position: absolute; top: 20px; left: 20px; }}
            .nav a {{ text-decoration: none; color: var(--primary); font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="nav"><a href="index.html">← Back to Raw Data</a></div>
        
        <div class="container">
            <header>
                <h1>🇨🇿 Czech Job Market Intelligence</h1>
                <div class="subtitle">Executive Overview • {datetime.now().strftime('%B %Y')} Edition</div>
            </header>

            <div class="grid">
                <!-- Salary Analysis -->
                <div class="card">
                    <h2>💰 Market Value by Role (Monthly CZK)</h2>
                    <div class="insight-box">
                        <strong>CEO Insight:</strong> Roles are ranked by average advertised salary. Use this to benchmark your internal compensation bands.
                    </div>
                    <canvas id="salaryChart"></canvas>
                </div>

                <!-- Modern Tech Stack -->
                <div class="card">
                    <h2>🔥 Top Technical Skills Demand</h2>
                    <div class="insight-box">
                        <strong>CTO Insight:</strong> Most frequently mentioned technical skills using accurate pattern matching. Note: Skills appear in only 1-5% of jobs, indicating specialized rather than universal demand.
                    </div>
                    <canvas id="skillChart"></canvas>
                </div>

                <!-- Top Hiring Volume -->
                <div class="card">
                    <h2>🏢 Top Hiring Volumes (Overall)</h2>
                    <div class="insight-box">
                        <strong>Market Share:</strong> Companies with the highest number of active job listings right now.
                    </div>
                    <canvas id="companyChart"></canvas>
                </div>

                <!-- Tech Hiring in Non-Tech -->
                <div class="card">
                    <h2>🤖 Hiring Volume in Modern Stack</h2>
                    <div class="insight-box">
                        <strong>Anomaly Detection:</strong> Companies hiring heavily for Modern Stack roles. Watch for non-tech firms (e.g., Retail, Banking) entering the talent war.
                    </div>
                    <canvas id="techHiringChart"></canvas>
                </div>
            </div>
            
            <footer style="text-align: center; margin-top: 60px; color: #94a3b8; font-size: 0.8rem;">
                Generated by JobsCzInsight Intelligence Engine • {datetime.now().strftime('%Y-%m-%d %H:%M')}
            </footer>
        </div>

        <script>
            Chart.defaults.font.family = "'Inter', sans-serif";
            Chart.defaults.color = '#64748b';

            // 1. Salary Chart
            new Chart(document.getElementById('salaryChart'), {{
                type: 'bar',
                data: {json.dumps(data['salary'])},
                options: {{
                    indexAxis: 'y',
                    plugins: {{ legend: {{ display: true }} }}
                }}
            }});

            // 2. Skill Chart
            new Chart(document.getElementById('skillChart'), {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(data['skills']['labels'])},
                    datasets: [{{
                        label: 'Job Mentions',
                        data: {json.dumps(data['skills']['data'])},
                        backgroundColor: '#f59e0b'
                    }}]
                }},
                options: {{
                    plugins: {{ legend: {{ display: false }} }}
                }}
            }});

            // 3. Top Companies
            new Chart(document.getElementById('companyChart'), {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(data['top_companies']['labels'])},
                    datasets: [{{
                        label: 'Active Listings',
                        data: {json.dumps(data['top_companies']['data'])},
                        backgroundColor: '#10b981'
                    }}]
                }},
                options: {{
                    indexAxis: 'y',
                    plugins: {{ legend: {{ display: false }} }}
                }}
            }});
            
            // 4. Tech Hiring Companies
            new Chart(document.getElementById('techHiringChart'), {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(data['tech_hiring']['labels'])},
                    datasets: [{{
                        label: 'Modern Stack Roles',
                        data: {json.dumps(data['tech_hiring']['data'])},
                        backgroundColor: '#6366f1'
                    }}]
                }},
                options: {{
                    indexAxis: 'y',
                    plugins: {{ legend: {{ display: false }} }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Executive Report generated: {OUTPUT_HTML}")

def main():
    try:
        conn = duckdb.connect(DB_PATH)
        data = get_market_intelligence(conn)
        generate_executive_report(data)
    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
