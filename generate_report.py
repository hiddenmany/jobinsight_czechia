import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import analyzer
import os
import datetime
import numpy as np
import json
from jinja2 import Environment, FileSystemLoader
from llm_analyzer import get_llm_insights
from dotenv import load_dotenv
from settings import settings

# Load environment variables
load_dotenv()

# --- SETUP ---
FORCE_REANALYZE = os.getenv('FORCE_REANALYZE', 'false').lower() == 'true'

if FORCE_REANALYZE:
    print("🔄 FORCE REANALYSIS enabled - Refreshing data...")
    write_core = analyzer.IntelligenceCore(read_only=False)
    write_core.reanalyze_all()
    write_core.con.close()
    print("✅ Reanalysis complete.")

# Load Data
intel = analyzer.MarketIntelligence()
df = intel.df
print(f"Generating Executive Radar with {len(df)} market signals.")

# --- LLM INSIGHTS (with Caching) ---
CACHE_PATH = str(settings.get_cache_path())
if os.path.exists(CACHE_PATH):
    print("📦 Loading AI Insights from cache...")
    with open(CACHE_PATH, 'r') as f:
        insights_list = json.load(f)
else:
    print("🧠 Generating fresh AI Insights with Gemini 3 Pro...")
    llm_insights = get_llm_insights(df)
    raw_insights = llm_insights.get('key_insights', []) if llm_insights.get('enabled') else []
    
    insights_list = []
    for i in raw_insights:
        if isinstance(i, str) and i.strip().startswith('{'):
            try:
                import ast
                insights_list.append(ast.literal_eval(i))
            except:
                insights_list.append({'title': 'Analysis', 'insight': i, 'emoji': '📊'})
        elif isinstance(i, dict):
            i.setdefault('metric_value', 0)
            i.setdefault('metric_name', 'Impact')
            i.setdefault('trend_direction', 'flat')
            insights_list.append(i)
    
    # Save to cache
    with open(CACHE_PATH, 'w') as f:
        json.dump(insights_list, f)

# --- KPI CALCULATION ---
valid_salaries = df[df['avg_salary'] > 0].copy()
jobs_with_salary = len(valid_salaries)

# 1. Median Salary (Whole Market)
median_salary_val = valid_salaries['avg_salary'].median()
kpi_median_salary = f"{int(median_salary_val):,} Kč".replace(',', ' ') if pd.notna(median_salary_val) else "N/A"

# 2. National Estimate (HPP only - aligns with ČSÚ scope)
hpp_only = valid_salaries[valid_salaries['contract_type'] == 'HPP']
hpp_median_val = hpp_only['avg_salary'].median()
kpi_hpp_median = f"{int(hpp_median_val):,} Kč".replace(',', ' ') if pd.notna(hpp_median_val) else "N/A"

# 3. ČSÚ Official Benchmark (Static)
CSU_OFFICIAL_MEDIAN = 41000 
kpi_csu_benchmark = f"{CSU_OFFICIAL_MEDIAN:,} Kč".replace(',', ' ')

# 4. Top Role
role_counts = df['role_type'].value_counts()
top_role = role_counts.index[0] if not role_counts.empty else "N/A"
top_role_count = role_counts.iloc[0] if not role_counts.empty else 0

# 5. Ghost Jobs
ghost_jobs = intel.get_ghost_jobs()
ghost_count = len(ghost_jobs)
ghost_rate = round((ghost_count / len(df)) * 100, 1) if len(df) > 0 else 0
ghost_color = "#EF4444" if ghost_rate > 5 else "#F59E0B" if ghost_rate > 2 else "#10B981"

# 6. Remote Work
remote_keywords = 'remote|home office|práce z domova|full-remote'
remote_count = df['description'].fillna('').str.contains(remote_keywords, case=False).sum()

remote_rate = round((remote_count / len(df)) * 100, 1) if len(df) > 0 else 0
remote_prem_data = intel.get_remote_salary_premium()
remote_premium = remote_prem_data.get('premium', 'N/A')

# 7. Tech Stack Health (Modern vs Dinosaur)
tech_status_counts = df['tech_status'].value_counts()
modern_count = int(tech_status_counts.get('Modern', 0))
dinosaur_count = int(tech_status_counts.get('Dinosaur', 0))
stable_count = int(tech_status_counts.get('Stable', 0))
total_classified = modern_count + dinosaur_count + stable_count

modern_rate = round((modern_count / total_classified) * 100, 1) if total_classified > 0 else 0
dinosaur_rate = round((dinosaur_count / total_classified) * 100, 1) if total_classified > 0 else 0
# Health score: higher Modern = better, higher Dinosaur = worse
tech_health_score = round(modern_rate - (dinosaur_rate * 2), 1)  # Penalize dinosaur more
tech_health_color = "#10B981" if tech_health_score > 5 else "#F59E0B" if tech_health_score >= 0 else "#EF4444"
tech_health_label = "Zdravý" if tech_health_score > 5 else "Neutrální" if tech_health_score >= 0 else "Zastaralý"

# --- VISUALS GENERATION ---

def _deep_convert(obj):
    """Recursively convert numpy arrays and other non-serializable types to Python lists."""
    if hasattr(obj, 'tolist'):  # numpy arrays
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: _deep_convert(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_deep_convert(item) for item in obj]
    elif isinstance(obj, (np.integer, np.floating)):
        return float(obj) if isinstance(obj, np.floating) else int(obj)
    else:
        return obj

def clean_json(fig):
    """Serialize Plotly figure to JSON safely for Plotly.js.
    
    Manually converts all numpy arrays to Python lists to avoid the 
    binary 'bdata' format that breaks rendering in Plotly.js.
    """
    # Convert to dict and recursively clean all numpy types
    fig_dict = fig.to_dict()
    clean_dict = _deep_convert(fig_dict)
    return json.dumps(clean_dict)


# Chart 1: Salary Box Plot (exclude "Other" and filter extreme salaries)
SALARY_CAP = 150000
top_roles_list = [r for r in role_counts.head(11).index.tolist() if r != 'Other'][:10]
box_df = valid_salaries[
    (valid_salaries['role_type'].isin(top_roles_list)) & 
    (valid_salaries['avg_salary'] <= SALARY_CAP)
].copy()
median_by_role = box_df.groupby('role_type')['avg_salary'].median().sort_values(ascending=True)
box_df['role_type'] = pd.Categorical(box_df['role_type'], categories=median_by_role.index, ordered=True)
box_df = box_df.sort_values('role_type')

fig_box = px.box(
    box_df,
    x='role_type',
    y='avg_salary',
    color='role_type',
    points=False,  # Hide outliers for cleaner visualization
    notched=False,
    color_discrete_sequence=px.colors.qualitative.Prism
)
fig_box.update_layout(
    yaxis_title='Monthly Salary (CZK)',
    xaxis_title='',
    showlegend=False,
    margin=dict(l=40, r=20, t=20, b=80),
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Plus Jakarta Sans', color='#64748B'),
    yaxis=dict(gridcolor='#E2E8F0'),
    xaxis=dict(tickangle=-45)
)

# Chart 2: Seniority Demand
seniority_order = ['Junior', 'Mid', 'Senior', 'Lead', 'Executive']
s_counts = df['seniority_level'].value_counts().reindex(seniority_order).fillna(0).reset_index()
s_counts.columns = ['Seniority', 'Count']
# DEBUG: Print to logs to verify counts
print(f"Seniority Counts for Chart:\n{s_counts}")

fig_pie = px.pie(
    s_counts,
    values='Count',
    names='Seniority',
    hole=0.6,
    color='Seniority',
    color_discrete_map={
        'Junior': '#BFDBFE',
        'Mid': '#60A5FA',
        'Senior': '#2563EB',
        'Lead': '#1E40AF',
        'Executive': '#0F172A'
    }
)
fig_pie.update_layout(
    margin=dict(l=20, r=20, t=20, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
    paper_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Plus Jakarta Sans', color='#64748B')
)

# Chart 3: Top Hiring Companies
top_companies = df[df['company'] != 'Unknown Employer']['company'].value_counts().head(10).reset_index()
top_companies.columns = ['Company', 'Count']
top_companies['Company'] = top_companies['Company'].apply(lambda x: x[:25] + '...' if len(x) > 25 else x)

fig_companies = px.bar(
    top_companies,
    x='Count',
    y='Company',
    orientation='h',
    text='Count' # Explicitly set text
)
fig_companies.update_traces(
    marker_color='#10B981', 
    textposition='auto', # Allow 'inside' if 'outside' gets clipped
    textfont_size=12
)
fig_companies.update_layout(
    yaxis={'categoryorder': 'total ascending'},
    margin=dict(l=20, r=20, t=20, b=20),
    xaxis_title='Active Roles',
    yaxis_title='',
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Plus Jakarta Sans', color='#64748B')
)

# Chart 4: Regional Treemap (Smarter Heatmap)
# Normalize city names and extract from "CZ" jobs where possible
def normalize_city(row):
    city = str(row['city']) if pd.notna(row['city']) else ''
    desc = str(row['description']) if pd.notna(row['description']) else ''
    
    # Praha variants
    if 'Praha' in city or 'prague' in city.lower() or city == 'Hlavní město Praha':
        return 'Praha'
    
    # If city is "CZ", try to extract from description
    if city == 'CZ':
        # Check for city mentions in description (ordered by likelihood)
        city_patterns = [
            ('Praha', ['Praha', 'Prague']),
            ('Brno', ['Brno']),
            ('Ostrava', ['Ostrava']),
            ('Plzeň', ['Plzeň', 'Pilsen']),
            ('Pardubice', ['Pardubice']),
            ('Olomouc', ['Olomouc']),
            ('Liberec', ['Liberec']),
            ('Hradec Králové', ['Hradec Králové']),
            ('České Budějovice', ['České Budějovice']),
            ('Zlín', ['Zlín']),
        ]
        for norm_name, patterns in city_patterns:
            if any(p in desc for p in patterns):
                return norm_name
        return 'Other'  # CZ with no identifiable city -> Other
    
    return city

city_normalized = df.apply(normalize_city, axis=1)

# Filter out "Other" for the treemap
city_counts = city_normalized.value_counts()
city_counts = city_counts[city_counts.index != 'Other'].head(12).reset_index()
city_counts.columns = ['City', 'Count']
city_counts['Region'] = 'Czechia' # Dummy parent for Treemap

fig_city = px.treemap(
    city_counts,
    path=['Region', 'City'],
    values='Count',
    color='Count',
    color_continuous_scale='Blues'
)
fig_city.update_traces(
    hovertemplate='<b>%{label}</b><br>Jobs: %{value:,}<extra></extra>'
)
fig_city.update_layout(
    margin=dict(l=10, r=10, t=10, b=10),
    paper_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Plus Jakarta Sans', color='#64748B')
)

# --- RENDERING ---
env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template('executive_dashboard.html')

now = datetime.datetime.now()
czech_months = {1: 'ledna', 2: 'února', 3: 'března', 4: 'dubna', 5: 'května', 6: 'června', 
                7: 'července', 8: 'srpna', 9: 'září', 10: 'října', 11: 'listopadu', 12: 'prosince'}
date_str = f"{now.day}. {czech_months[now.month]} {now.year}"
time_str = now.strftime('%H:%M')

# Get unique values for filters
available_roles = sorted(df['role_type'].dropna().unique().tolist())

# Clean city filter: use top cities by count, exclude junk values
city_counts_for_filter = city_normalized.value_counts()
# Filter out junk: must not contain company indicators and must be reasonable length
junk_indicators = ['s.r.o', 'a.s.', 'spol.', 'GmbH', 'Ltd', 'Inc', '@', 'www.', 'http', 'Other']
clean_cities = [
    city for city in city_counts_for_filter.head(30).index.tolist()
    if city and len(str(city)) < 30 and not any(junk in str(city) for junk in junk_indicators)
]
available_cities = clean_cities[:15]  # Top 15 clean cities

# Prepare raw data for client-side filtering
df_for_export = df[['role_type', 'seniority_level', 'avg_salary', 'company', 'contract_type']].copy()
df_for_export['city'] = city_normalized
df_for_export = df_for_export.fillna('')
# Convert to records for JSON
raw_data_json = json.dumps(df_for_export.to_dict(orient='records'), default=str)

html_output = template.render(
    generation_date=date_str,
    generation_time=time_str,
    total_jobs=len(df),
    jobs_with_salary=jobs_with_salary,
    kpi_median_salary=kpi_median_salary,
    kpi_hpp_median=kpi_hpp_median,
    kpi_csu_benchmark=kpi_csu_benchmark,
    kpi_top_role=top_role,
    kpi_top_role_count=top_role_count,
    kpi_ghost_rate=ghost_rate,
    kpi_ghost_count=ghost_count,
    kpi_ghost_color=ghost_color,
    kpi_remote_rate=remote_rate,
    kpi_remote_premium=remote_premium,
    
    # Tech Stack Health KPIs
    kpi_modern_count=modern_count,
    kpi_modern_rate=modern_rate,
    kpi_dinosaur_count=dinosaur_count,
    kpi_dinosaur_rate=dinosaur_rate,
    kpi_tech_health_score=tech_health_score,
    kpi_tech_health_color=tech_health_color,
    kpi_tech_health_label=tech_health_label,
    
    salary_box_plot_json=clean_json(fig_box),
    seniority_pie_json=clean_json(fig_pie),
    top_companies_json=clean_json(fig_companies),
    city_chart_json=clean_json(fig_city),
    
    llm_insights=insights_list,
    available_roles=available_roles,
    available_cities=available_cities,
    raw_data_json=raw_data_json
)

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(html_output)

print(f"🚀 Executive Radar v2.2 generated with Gemini 3 Pro Preview: {os.path.abspath('public/index.html')}")