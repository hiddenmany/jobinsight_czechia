import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import analyzer
import os
import datetime
import numpy as np
import json
from jinja2 import Environment, FileSystemLoader

# Setup
pd.set_option('display.max_columns', None)

# FORCE REANALYSIS - Check flag BEFORE opening any database connections
# TODO: Remove after database is updated with new role taxonomy (v1.5 classification update)
FORCE_REANALYZE = os.getenv('FORCE_REANALYZE', 'true').lower() == 'true'

if FORCE_REANALYZE:
    print("🔄 FORCE REANALYSIS enabled - Applying updated role classification logic...")
    # Open in write mode, do reanalysis, then close
    write_core = analyzer.IntelligenceCore(read_only=False)
    print(f"Loaded {len(write_core.load_as_df())} market signals for reanalysis.")
    write_core.reanalyze_all()
    write_core.con.close()
    print("✅ Reanalysis complete. Loading updated data...")

# Now load data for report generation (read-only)
intel = analyzer.MarketIntelligence()
df = intel.df
print(f"Generating v1.0 HR Intelligence report with {len(df)} market signals.")

# Auto-Recovery: If Tech Status or Role Type is missing, force re-analysis
if not FORCE_REANALYZE and (df['tech_status'].isnull().mean() > 0.5 or df['role_type'].isnull().mean() > 0.5 or df.empty):
    print("⚠️ Detected missing NLP/HR data. Running v1.0 re-analysis...")
    intel.core.con.close()  # Close read-only connection first
    write_core = analyzer.IntelligenceCore(read_only=False)
    write_core.reanalyze_all()
    write_core.con.close()
    # Reload
    intel = analyzer.MarketIntelligence()
    df = intel.df

# --- KPI CALCULATION ---
valid_salaries = df[df['avg_salary'] > 0]
med_sal = valid_salaries['avg_salary'].median()
med_sal_fmt = int(med_sal/1000) if pd.notna(med_sal) else "N/A"

# Tech Premium (Modern vs Dinosaur)
modern_sal = valid_salaries[valid_salaries['tech_status'] == 'Modern']['avg_salary'].median()
legacy_sal = valid_salaries[valid_salaries['tech_status'] == 'Dinosaur']['avg_salary'].median()

if pd.notna(modern_sal) and pd.notna(legacy_sal) and legacy_sal > 0:
    tech_premium_val = int(((modern_sal / legacy_sal) - 1) * 100)
    tech_premium = f"+{tech_premium_val}%" if tech_premium_val >= 0 else f"{tech_premium_val}%"
else:
    tech_premium = "N/A"

# v1.0: Seniority Premium (Senior vs Junior)
senior_sal = valid_salaries[valid_salaries['seniority_level'] == 'Senior']['avg_salary'].median()
junior_sal = valid_salaries[valid_salaries['seniority_level'] == 'Junior']['avg_salary'].median()
if pd.notna(senior_sal) and pd.notna(junior_sal) and junior_sal > 0:
    seniority_premium_val = int(((senior_sal / junior_sal) - 1) * 100)
    seniority_premium = f"+{seniority_premium_val}%" if seniority_premium_val >= 0 else f"{seniority_premium_val}%"
else:
    seniority_premium = "N/A"

# Robust KPI extraction
lang_barrier = intel.get_language_barrier()
en_share = int(lang_barrier.get('English Friendly', 0) / len(df) * 100) if len(df) > 0 else 0

# --- CHART GENERATION (JSON) ---
layout_defaults = dict(
    margin=dict(l=20,r=20,t=30,b=20),
    xaxis=dict(automargin=True),
    yaxis=dict(automargin=True),
    height=300,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Inter, sans-serif', color='#111')
)

# Source Distribution - REMOVED (user request)
# Print stats for debugging
vol_stats = df['source'].value_counts().reset_index()
vol_stats.columns = ['Source', 'Count']
print(f"Source Stats:\n{vol_stats}")

# --- 2. Contract Types ---
contract_split = intel.get_contract_split()
# Sanitize data for Plotly (convert to python primitives)
cont_values = [int(v) for v in contract_split.values()]
cont_names = list(contract_split.keys())

print(f"Contract Types - Names: {cont_names}")
print(f"Contract Types - Values: {cont_values}")

# Use go.Pie for better control and reliability
fig_cont = go.Figure(data=[go.Pie(
    labels=cont_names,
    values=cont_values,
    hole=0.6,
    textposition='inside',
    textinfo='percent+label'
)])
fig_cont.update_layout(**layout_defaults, showlegend=True)

# --- 3. Tech Stack Gap ---
tech_lag = intel.get_tech_stack_lag().reset_index()
tech_lag.columns = ['Status', 'Count']
# Explicit list conversion
t_status = tech_lag['Status'].tolist()
t_counts = [int(x) for x in tech_lag['Count'].tolist()]

# Use go.Bar for better control and reliability
color_map = {'Modern': '#0055FF', 'Stable': '#999999', 'Dinosaur': '#333333'}
bar_colors = [color_map.get(s, '#999999') for s in t_status]

fig_tech = go.Figure(data=[go.Bar(
    x=t_counts,
    y=t_status,
    orientation='h',
    marker=dict(color=bar_colors)
)])
fig_tech.update_layout(**layout_defaults)
fig_tech.update_yaxes(categoryorder='array', categoryarray=['Dinosaur', 'Stable', 'Modern'], title="Status")
fig_tech.update_xaxes(title="Count")

# Salary by Platform - REMOVED (user request - redundant data)

# 5. Top Innovators (keep existing)
modern_df = df[(df['tech_status'] == 'Modern') & (df['company'] != 'Unknown Employer')]
top_innovators = modern_df.groupby('company').agg(
    count=('hash', 'count'),
    avg_sal=('avg_salary', lambda x: x[x>0].median())
).sort_values('count', ascending=False).head(10)

innovators = []
for company, row in top_innovators.iterrows():
    clean_company = company.lstrip('•\u2022\u2023\u25E6\u25AA\u25AB').strip()
    clean_company = ' '.join(clean_company.split())
    sal_display = f"{int(row['avg_sal']/1000)}k" if pd.notna(row['avg_sal']) and row['avg_sal'] > 0 else "N/A"
    innovators.append({
        "company": clean_company,
        "count": int(row['count']),
        "avg_sal": sal_display
    })

# --- v1.0 HR INTELLIGENCE CHARTS ---

# 6. Salary by Role (NEW) - with sample sizes
role_sal = intel.get_salary_by_role()
if not role_sal.empty:
    # List conversion - add sample sizes to labels
    r_types_raw = role_sal['role_type'].tolist()
    r_counts = role_sal['count'].tolist()
    r_types = [f"{role} (n={int(cnt)})" for role, cnt in zip(r_types_raw, r_counts)]
    r_salaries = [float(x) for x in role_sal['median_salary'].tolist()]

    fig_role = go.Figure(data=[go.Bar(
        x=r_salaries,
        y=r_types,
        orientation='h',
        marker=dict(color='#0055FF')
    )])
    role_layout = {**layout_defaults, 'height': max(280, len(r_types) * 25)}
    fig_role.update_layout(**role_layout)
    fig_role.update_yaxes(title="")
    fig_role.update_xaxes(title="Median Salary (CZK)")
else:
    fig_role = go.Figure()
    fig_role.update_layout(**layout_defaults)

# 7. Salary by Seniority (NEW)
seniority_sal = intel.get_salary_by_seniority()
if not seniority_sal.empty:
    # List conversion
    s_levels = seniority_sal['seniority_level'].tolist()
    s_salaries = [float(x) for x in seniority_sal['median_salary'].tolist()]

    colors = {'Junior': '#66B2FF', 'Mid': '#0055FF', 'Senior': '#003399', 'Lead': '#001a4d', 'Executive': '#000033'}
    # Map colors manually since we are passing lists
    s_colors = [colors.get(l, '#0055FF') for l in s_levels]

    fig_seniority = go.Figure(data=[go.Bar(
        x=s_levels,
        y=s_salaries,
        marker=dict(color=s_colors)
    )])
    seniority_layout = {**layout_defaults, 'height': 280, 'showlegend': False}
    fig_seniority.update_layout(**seniority_layout)
    fig_seniority.update_yaxes(title="Median Salary (CZK)")
    fig_seniority.update_xaxes(title="")
else:
    fig_seniority = go.Figure()
    fig_seniority.update_layout(**layout_defaults)

# 8. Role Distribution (NEW - for insights)
role_dist = intel.get_role_distribution()
role_dist.columns = ['Role', 'Count']
top_roles = role_dist.head(5).to_dict('records')

# 9. Skill Premiums (NEW)
skill_premiums = intel.get_skill_premiums()
skill_data = skill_premiums.head(10).to_dict('records') if not skill_premiums.empty else []

# 10. Seniority + Role Cross-Analysis (v1.1 - Data Quality Insight)
seniority_role_matrix = intel.get_seniority_role_matrix()
seniority_role_data = seniority_role_matrix.to_dict('records') if not seniority_role_matrix.empty else []

# --- v1.1 BENEFITS INTELLIGENCE ---
print("\n=== Analyzing Benefits ===")
benefits_analysis = intel.get_benefits_analysis()
benefits_data = benefits_analysis.to_dict('records') if not benefits_analysis.empty else []
print(f"Found {len(benefits_data)} benefit types")

benefits_by_role = intel.get_benefits_by_role()
benefits_role_data = benefits_by_role.to_dict('records') if not benefits_by_role.empty else []

# --- v1.1 LOCATION INTELLIGENCE ---
print("\n=== Analyzing Locations ===")
salary_by_city = intel.get_salary_by_city()
city_salary_data = salary_by_city.to_dict('records') if not salary_by_city.empty else []
print(f"Found salary data for {len(city_salary_data)} cities")

location_dist = intel.get_location_distribution()
location_data = location_dist.to_dict('records') if not location_dist.empty else []

# --- v1.1 WORK MODEL INTELLIGENCE ---
print("\n=== Analyzing Work Models ===")
work_model_dist = intel.get_work_model_distribution()
print(f"Work model distribution: {work_model_dist}")

remote_premium = intel.get_remote_salary_premium()
print(f"Remote salary premium: {remote_premium.get('premium', 'N/A')}")

work_model_by_role = intel.get_work_model_by_role()
work_model_role_data = work_model_by_role.to_dict('records') if not work_model_by_role.empty else []

# --- v1.2 TEMPORAL & EMERGING TRENDS ---
print("\n=== Analyzing Trends & Signals ===")
data_freshness = intel.get_data_freshness_report()
print(f"Data coverage: {data_freshness['unique_dates']} day(s)")
print(f"Trend analysis ready: {data_freshness['trend_analysis_ready']}")

# Salary trends (only if 7+ days)
salary_trend = intel.get_salary_trend_weekly()
trend_data = salary_trend.to_dict('records') if not salary_trend.empty else []

# Emerging signals (works with any amount of data)
emerging_tech = intel.get_emerging_tech_signals()
emerging_tech_data = emerging_tech.to_dict('records') if not emerging_tech.empty else []
print(f"Found {len(emerging_tech_data)} hot technologies")

new_entrants = intel.get_new_market_entrants()
new_entrants_data = new_entrants.to_dict('records') if not new_entrants.empty else []
print(f"Found {len(new_entrants_data)} emerging companies")

trending_benefits = intel.get_trending_benefits()
trending_benefits_data = trending_benefits.to_dict('records') if not trending_benefits.empty else []

# --- MARKET TRENDS & DEEP ANALYSIS ---
print("\n=== Analyzing Market Trends ===")

# Salary Percentiles by Role (25th/50th/75th) - like original trends.html
salary_percentiles_by_role = []
valid_salaries_df = df[df['avg_salary'] > 0].copy()

# DIAGNOSTIC: Show salary data availability per role
print("\n=== SALARY DATA AVAILABILITY BY ROLE ===")
salary_counts = df.groupby('role_type').agg(
    total_jobs=('hash', 'count'),
    jobs_with_salary=('avg_salary', lambda x: (x > 0).sum())
).sort_values('total_jobs', ascending=False)
print(salary_counts.head(15))
print(f"Total jobs: {len(df)}, Jobs with salary: {len(valid_salaries_df)} ({len(valid_salaries_df)/len(df)*100:.1f}%)")

if not valid_salaries_df.empty and 'role_type' in valid_salaries_df.columns:
    role_percentiles = valid_salaries_df.groupby('role_type')['avg_salary'].agg([
        ('p25', lambda x: x.quantile(0.25)),
        ('median', lambda x: x.quantile(0.50)),
        ('p75', lambda x: x.quantile(0.75)),
        ('count', 'count')
    ]).reset_index()
    # Lower threshold and add sample size to labels
    role_percentiles = role_percentiles[role_percentiles['count'] >= 1].sort_values('median', ascending=False).head(15)
    role_percentiles['role_label'] = role_percentiles.apply(
        lambda row: f"{row['role_type']} (n={int(row['count'])})", axis=1
    )
    
    # Create Plotly grouped bar chart for percentiles - use labels with sample sizes
    r_types_pct = role_percentiles['role_label'].tolist()
    r_p25 = [float(x) for x in role_percentiles['p25'].tolist()]
    r_median = [float(x) for x in role_percentiles['median'].tolist()]
    r_p75 = [float(x) for x in role_percentiles['p75'].tolist()]
    
    fig_salary_percentiles = go.Figure()
    fig_salary_percentiles.add_trace(go.Bar(
        y=r_types_pct,
        x=r_p25,
        name='25th Percentile (Conservative)',
        orientation='h',
        marker=dict(color='#FFCE56')
    ))
    fig_salary_percentiles.add_trace(go.Bar(
        y=r_types_pct,
        x=r_median,
        name='Median Advertised Salary',
        orientation='h',
        marker=dict(color='#36A2EB')
    ))
    fig_salary_percentiles.add_trace(go.Bar(
        y=r_types_pct,
        x=r_p75,
        name='75th Percentile (Aspirational)',
        orientation='h',
        marker=dict(color='#FF6384')
    ))
    
    percentile_layout = {**layout_defaults, 'height': 400, 'barmode': 'group'}
    fig_salary_percentiles.update_layout(**percentile_layout)
    fig_salary_percentiles.update_yaxes(title="")
    fig_salary_percentiles.update_xaxes(title="Monthly CZK")
    print(f"Generated salary percentiles for {len(r_types_pct)} roles")
else:
    fig_salary_percentiles = go.Figure()
    fig_salary_percentiles.update_layout(**layout_defaults)

# Top Companies by Hiring Volume (all companies) - Convert to Plotly chart
top_companies_df = df[df['company'] != 'Unknown Employer'].groupby('company').size().reset_index(name='count').sort_values('count', ascending=False).head(15)
top_companies_list = []
comp_names = []
comp_counts = []
for _, row in top_companies_df.iterrows():
    clean_company = row['company'].lstrip('•◦◦▦▪▫').strip()
    clean_company = ' '.join(clean_company.split())
    top_companies_list.append(clean_company)
    comp_counts.append(int(row['count']))
    comp_names.append(clean_company)

fig_top_companies = go.Figure(data=[go.Bar(
    y=comp_names[::-1],  # Reverse to show highest at top
    x=comp_counts[::-1],
    orientation='h',
    marker=dict(color='#10b981')
)])
companies_layout = {**layout_defaults, 'height': 400}
fig_top_companies.update_layout(**companies_layout)
fig_top_companies.update_yaxes(title="")
fig_top_companies.update_xaxes(title="Active Listings")
print(f"Found {len(comp_names)} top hiring companies")

# Top Skills by Frequency - Convert to Plotly chart
top_skills_list = []
skill_names = []
skill_counts = []
if not emerging_tech.empty:
    for _, row in emerging_tech.head(15).iterrows():
        skill_name = row['Technology']
        skill_count = int(row['Jobs'])
        top_skills_list.append(skill_name)
        skill_names.append(skill_name)
        skill_counts.append(skill_count)

fig_top_skills = go.Figure(data=[go.Bar(
    x=skill_names,
    y=skill_counts,
    marker=dict(color='#f59e0b')
)])
skills_layout = {**layout_defaults, 'height': 350}
fig_top_skills.update_layout(**skills_layout)
fig_top_skills.update_xaxes(title="", tickangle=-45)
fig_top_skills.update_yaxes(title="Job Mentions")
print(f"Found {len(skill_names)} top skills")

# Role Distribution Chart (like original trends.html)
role_dist_chart = intel.get_role_distribution().head(15)
role_labels = role_dist_chart.iloc[:, 0].tolist()
role_counts_chart = [int(x) for x in role_dist_chart.iloc[:, 1].tolist()]

fig_role_distribution = go.Figure(data=[go.Bar(
    y=role_labels[::-1],
    x=role_counts_chart[::-1],
    orientation='h',
    marker=dict(color='#6366f1')
)])
role_dist_layout = {**layout_defaults, 'height': 400}
fig_role_distribution.update_layout(**role_dist_layout)
fig_role_distribution.update_yaxes(title="")
fig_role_distribution.update_xaxes(title="Active Listings")

# --- v1.3 ECONOMIC REALITY & TALENT DYNAMICS ---
print("\n=== Analyzing Economic Reality ===")

# 1. IČO vs HPP Arbitrage
ico_arbitrage = intel.get_ico_hpp_arbitrage()
print(f"IČO vs HPP premium: {ico_arbitrage.get('premium', 'N/A')} (IČO: {ico_arbitrage['ico_count']}, HPP: {ico_arbitrage['hpp_count']})")

# 2. Language Barrier Cost
lang_barrier = intel.get_language_barrier_cost()
print(f"English language premium: {lang_barrier.get('premium', 'N/A')}")

# 3. Talent Pipeline Health
pipeline_health = intel.get_talent_pipeline_health()
print(f"Junior:Senior ratio: {pipeline_health.get('ratio', 'N/A')} - {pipeline_health.get('health', 'Unknown')}")

# 4. Remote Flexibility
remote_flex = intel.get_remote_flexibility_analysis()
remote_flex_data = remote_flex.to_dict('records') if not remote_flex.empty else []

# 5. Legacy Rot
legacy_rot = intel.get_legacy_rot_by_role()
legacy_rot_data = legacy_rot.to_dict('records') if not legacy_rot.empty else []

# 6. AI Washing
ai_washing = intel.get_ai_washing_nontech()
print(f"AI washing in non-tech: {ai_washing.get('percentage', 'N/A')}")

# 7. Ghost Jobs
ghost_jobs = intel.get_ghost_jobs()
ghost_jobs_data = ghost_jobs.to_dict('records') if not ghost_jobs.empty else []
print(f"Potential ghost jobs detected: {len(ghost_jobs_data)}")

# --- RENDER ---
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
env = Environment(loader=FileSystemLoader(template_dir))

# v1.3 Localization dictionary
t_cz = {
    'roles': {
        'Developer': 'Vývojář', 'Analyst': 'Analytik', 'Designer': 'Designér',
        'QA': 'QA/Tester', 'PM': 'Projektový Manažer', 'Sales': 'Obchod/Sales',
        'HR': 'HR/Nábor', 'Marketing': 'Marketing', 'Support': 'Podpora',
        'Operations': 'Provoz/Ops', 'Finance': 'Finance/Účetní', 'Management': 'Management',
        'Other': 'Ostatní', 'Unknown': 'Neznámé'
    },
    'seniority': {
        'Junior': 'Junior', 'Mid': 'Medior/Mid', 'Senior': 'Senior',
        'Lead': 'Lead/Expert', 'Executive': 'Executive/Vedení', 'Unknown': 'Neznámé'
    },
    'benefits': {
        'Meal Vouchers': 'Stravenky', 'Fitness/MultiSport': 'MultiSport/Fitness',
        'Education Budget': 'Vzdělávací rozpočet', 'Home Office Equipment': 'Příspěvek na Home Office',
        'Stock Options/Equity': 'Akcie/ESOP', 'Performance Bonuses': 'Výkonnostní bonusy',
        '13th/14th Salary': '13./14. plat', 'Paid Sick Days': 'Sick Days',
        'Extra Vacation Days': 'Dovolená navíc', 'Wellness Programs': 'Wellness/Relaxace',
        'Parental Benefits': 'Rodičovské benefity', 'Pension Contribution': 'Penzijní připojištění',
        'Flexible Benefits (Cafeteria)': 'Kafetérie'
    },
    'work_models': {
        'Full Remote': 'Plný Remote', 'Hybrid': 'Hybridní', 'Office Only': 'Kancelář',
        'Rigid (Fixed Days)': 'Fixní dny (Rigidní)', 'Flexible': 'Flexibilní', 'Unclear': 'Nejasné'
    },
    'flexibility': {
        'Rigid (Fixed Days)': 'Fixní dny', 'Flexible': 'Flexibilní', 'Unclear': 'Nejasné'
    },
    'tech_status': {
        'Modern': 'Moderní', 'Stable': 'Stabilní', 'Dinosaur': 'Zastaralé'
    }
}

# Custom filter for translations
def translate_cz(value, category):
    if not value: return value
    return t_cz.get(category, {}).get(value, value)

env.filters['translate_cz'] = translate_cz

template = env.get_template('report.html')

# Helper to ensure clean JSON serialization without binary artifacts
def clean_json(fig):
    def default_parser(o):
        if isinstance(o, (np.int64, np.integer)):
            return int(o)
        elif isinstance(o, (np.float64, np.floating)):
            return float(o)
        elif isinstance(o, np.ndarray):
            return o.tolist()
        return str(o)
    return json.dumps(fig.to_dict(), default=default_parser)

# --- v1.4 CONTRACT SALARY SPLIT ---
contract_salaries = intel.get_salary_by_contract_type()
hpp_med = contract_salaries.get('HPP', 0)
brig_med = contract_salaries.get('Brigáda', 0)

hpp_median_fmt = f"{int(hpp_med/1000)}" if hpp_med > 0 else "N/A"
brig_median_fmt = f"{int(brig_med/1000)}" if brig_med > 0 else "N/A"

# --- EXECUTIVE SUMMARY KPIS ---
# Get top 3 roles by volume
top_3_roles = [f"{r['Role']} ({r['Count']})" for r in top_roles[:3]]

summary_kpis = {
    'total_jobs': len(df),
    'hpp_median': hpp_median_fmt,
    'tech_premium': tech_premium,
    'top_role_1': top_roles[0]['Role'] if top_roles else "N/A",
    'top_role_count': top_roles[0]['Count'] if top_roles else 0,
    'remote_share': f"{work_model_dist.get('Full Remote', 0)/len(df)*100:.1f}%" if len(df) > 0 else "0%",
    'ico_premium': ico_arbitrage.get('premium', 'N/A'),
    'ghost_jobs': len(ghost_jobs_data),
    'ai_washing': ai_washing.get('percentage', 'N/A'),
    'last_updated': datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
}

template_vars = dict(
    summary_kpis=summary_kpis,  # NEW Phase 1
    date=datetime.date.today().strftime("%d. %B %Y"),
    total_jobs=len(df),
    med_salary=med_sal_fmt,
    hpp_median=hpp_median_fmt,      # NEW
    brig_median=brig_median_fmt,    # NEW
    tech_premium=tech_premium,
    seniority_premium=seniority_premium,  # NEW v1.0
    en_share=en_share,
    innovators=innovators,
    top_roles=top_roles,  # NEW v1.0
    skill_premiums=skill_data,  # NEW v1.0
    seniority_role_matrix=seniority_role_data,  # NEW v1.1 - Data Quality Insight
    # v1.1 Benefits Intelligence
    benefits_data=benefits_data,
    benefits_by_role=benefits_role_data,
    # v1.1 Location Intelligence
    city_salary_data=city_salary_data,
    location_data=location_data,
    # v1.1 Work Model Intelligence
    work_model_dist=work_model_dist,
    remote_premium=remote_premium,
    work_model_by_role=work_model_role_data,
    # v1.2 Temporal & Emerging Trends
    data_freshness=data_freshness,
    salary_trend=trend_data,
    emerging_tech=emerging_tech_data,
    new_entrants=new_entrants_data,
    trending_benefits=trending_benefits_data,
    # Market Trends & Deep Analysis - Charts
    json_salary_percentiles=clean_json(fig_salary_percentiles),
    json_top_companies=clean_json(fig_top_companies),
    json_top_skills=clean_json(fig_top_skills),
    json_role_distribution=clean_json(fig_role_distribution),
    # v1.3 Economic Reality & Talent Dynamics
    ico_arbitrage=ico_arbitrage,
    lang_barrier=lang_barrier,
    pipeline_health=pipeline_health,
    remote_flex=remote_flex_data,
    legacy_rot=legacy_rot_data,
    ai_washing=ai_washing,
    ghost_jobs=ghost_jobs_data,
    # Charts
    json_contract=clean_json(fig_cont),
    json_tech=clean_json(fig_tech),
    json_role=clean_json(fig_role),  # NEW v1.0
    json_seniority=clean_json(fig_seniority)  # NEW v1.0
)

output_html = template.render(**template_vars)

base_dir = os.path.dirname(os.path.abspath(__file__))
public_dir = os.path.join(base_dir, "public")
os.makedirs(public_dir, exist_ok=True)

with open(os.path.join(public_dir, "index.html"), "w", encoding="utf-8") as f:
    f.write(output_html)

print(f"v1.0 HR Intelligence report generated: {os.path.join(public_dir, 'index.html')}")

# --- CZECH VERSION ---
# Czech date format with Czech month names
czech_months = {
    1: 'ledna', 2: 'února', 3: 'března', 4: 'dubna',
    5: 'května', 6: 'června', 7: 'července', 8: 'srpna',
    9: 'září', 10: 'října', 11: 'listopadu', 12: 'prosince'
}
today = datetime.date.today()
czech_date = f"{today.day}. {czech_months[today.month]} {today.year}"

template_cz = env.get_template('report_cz.html')
output_html_cz = template_cz.render(
    date=czech_date,
    total_jobs=len(df),
    med_salary=med_sal_fmt,
    tech_premium=tech_premium,
    seniority_premium=seniority_premium,
    en_share=en_share,
    innovators=innovators,
    top_roles=top_roles,
    skill_premiums=skill_data,
    seniority_role_matrix=seniority_role_data,
    benefits_data=benefits_data,
    benefits_by_role=benefits_role_data,
    city_salary_data=city_salary_data,
    location_data=location_data,
    work_model_dist=work_model_dist,
    remote_premium=remote_premium,
    work_model_by_role=work_model_role_data,
    data_freshness=data_freshness,
    salary_trend=trend_data,
    emerging_tech=emerging_tech_data,
    new_entrants=new_entrants_data,
    trending_benefits=trending_benefits_data,
    json_salary_percentiles=clean_json(fig_salary_percentiles),
    json_top_companies=clean_json(fig_top_companies),
    json_top_skills=clean_json(fig_top_skills),
    json_role_distribution=clean_json(fig_role_distribution),
    ico_arbitrage=ico_arbitrage,
    lang_barrier=lang_barrier,
    pipeline_health=pipeline_health,
    remote_flex=remote_flex_data,
    legacy_rot=legacy_rot_data,
    ai_washing=ai_washing,
    ghost_jobs=ghost_jobs_data,
    json_contract=clean_json(fig_cont),
    json_tech=clean_json(fig_tech),
    json_role=clean_json(fig_role),
    json_seniority=clean_json(fig_seniority)
)

with open(os.path.join(public_dir, "index_cz.html"), "w", encoding="utf-8") as f:

    f.write(output_html_cz)



print(f"v1.0 Czech version generated: {os.path.join(public_dir, 'index_cz.html')}")
