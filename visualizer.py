import duckdb
import json
import os
from datetime import datetime

# Configuration
DB_PATH = 'data/intelligence.db'
OUTPUT_HTML = 'public/trends.html'

# Skills to track (English & Czech variations could be added)
SKILLS = [
    "Python", "Java", "JavaScript", "TypeScript", "React", "Angular", "Vue", 
    "SQL", "PostgreSQL", "MongoDB", "AWS", "Azure", "Docker", "Kubernetes",
    "Excel", "SAP", "English", "Němčina", "Project Management", "Agile"
]

def get_trend_data(conn):
    print("Generating Trend Data...")
    # Group by Date (Day) and Role
    query = """
        SELECT 
            strftime(scraped_at, '%Y-%m-%d') as scrape_date,
            role_type,
            COUNT(*) as job_count
        FROM signals
        WHERE role_type IS NOT NULL
        GROUP BY 1, 2
        ORDER BY 1, 2
    """
    results = conn.execute(query).fetchall()
    
    # Structure for Chart.js: { dates: [], datasets: [ { label: 'Role', data: [] } ] }
    data_map = {}
    dates = set()
    
    for date, role, count in results:
        dates.add(date)
        if role not in data_map:
            data_map[role] = {}
        data_map[role][date] = count
        
    sorted_dates = sorted(list(dates))
    
    datasets = []
    # colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']
    
    for role, dates_counts in data_map.items():
        data_points = []
        for d in sorted_dates:
            data_points.append(dates_counts.get(d, 0))
            
        datasets.append({
            "label": role,
            "data": data_points,
            "fill": False,
            "tension": 0.1
        })
        
    return {
        "labels": sorted_dates,
        "datasets": datasets
    }

def get_skill_heatmap(conn):
    print("Generating Skill Heatmap...")
    # This is expensive, so we do it simply:
    # For each skill, count how many descriptions contain it
    
    skill_counts = []
    
    for skill in SKILLS:
        # Simple case-insensitive match. 
        # refined: use word boundaries if possible, but LIKE %...% is faster/easier for now
        query = f"""
            SELECT COUNT(*) 
            FROM signals 
            WHERE lower(description) LIKE '%{skill.lower()}%'
        """
        count = conn.execute(query).fetchone()[0]
        skill_counts.append({"skill": skill, "count": count})
    
    # Sort by count desc
    skill_counts.sort(key=lambda x: x['count'], reverse=True)
    
    return {
        "labels": [x['skill'] for x in skill_counts],
        "datasets": [{
            "label": 'Mentions in Job Descriptions',
            "data": [x['count'] for x in skill_counts],
            "backgroundColor": 'rgba(54, 162, 235, 0.6)'
        }]
    }

def generate_html(trend_data, skill_data):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>JobsCz Insights - Trends</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; background: #f4f4f9; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; }}
            h1 {{ color: #333; }}
            h2 {{ border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            .nav {{ margin-bottom: 20px; }}
            .nav a {{ margin-right: 15px; text-decoration: none; color: #007bff; font-weight: bold; }}
            canvas {{ max-height: 400px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>JobsCz Market Insights</h1>
            <div class="nav">
                <a href="index.html">← Back to Job List</a>
            </div>

            <div class="card">
                <h2>Job Volume by Role (Trends)</h2>
                <canvas id="trendChart"></canvas>
            </div>

            <div class="card">
                <h2>Top Skills Demand (Keyword Frequency)</h2>
                <p>Based on analysis of {sum(skill_data['datasets'][0]['data'])} keyword matches across database.</p>
                <canvas id="skillChart"></canvas>
            </div>
            
            <footer style="text-align: center; color: #777; margin-top: 40px;">
                Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} | Powered by DuckDB & JobsCzInsight
            </footer>
        </div>

        <script>
            // Trend Chart
            const trendCtx = document.getElementById('trendChart').getContext('2d');
            new Chart(trendCtx, {{
                type: 'line',
                data: {json.dumps(trend_data)},
                options: {{
                    responsive: true,
                    interaction: {{ mode: 'index', intersect: false }},
                    plugins: {{
                        legend: {{ position: 'right' }}
                    }}
                }}
            }});

            // Skill Chart
            const skillCtx = document.getElementById('skillChart').getContext('2d');
            new Chart(skillCtx, {{
                type: 'bar',
                data: {json.dumps(skill_data)},
                options: {{
                    indexAxis: 'y',
                    responsive: true,
                    plugins: {{
                        legend: {{ display: false }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Report generated: {OUTPUT_HTML}")

def main():
    try:
        conn = duckdb.connect(DB_PATH)
        trend_data = get_trend_data(conn)
        skill_data = get_skill_heatmap(conn)
        generate_html(trend_data, skill_data)
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    main()
