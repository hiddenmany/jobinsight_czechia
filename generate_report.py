import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import analyzer
import os
import datetime
from jinja2 import Environment, FileSystemLoader

# Setup
intel = analyzer.MarketIntelligence()
df = intel.df
print(f"Generating report with {len(df)} market signals.")

# --- KPI CALCULATION ---
valid_salaries = df[df['avg_salary'] > 0]
med_sal = valid_salaries['avg_salary'].median()
med_sal_fmt = int(med_sal/1000) if pd.notna(med_sal) else "N/A"

# Tech Premium (Modern vs Dinosaur)
modern_sal = valid_salaries[valid_salaries['tech_status'] == 'Modern']['avg_salary'].median()
legacy_sal = valid_salaries[valid_salaries['tech_status'] == 'Dinosaur']['avg_salary'].median()
tech_premium = int(((modern_sal / legacy_sal) - 1) * 100) if pd.notna(modern_sal) and pd.notna(legacy_sal) and legacy_sal > 0 else 0

# Robust KPI extraction
lang_barrier = intel.get_language_barrier()
en_share = int(lang_barrier.get('English Friendly', 0) / len(df) * 100) if len(df) > 0 else 0

# --- CHART GENERATION (JSON) ---
layout_defaults = dict(
    margin=dict(l=0,r=0,t=0,b=0),
    height=300,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Inter, sans-serif', color='#111')
)

# 1. Source Distribution
vol_stats = df['source'].value_counts().reset_index()
vol_stats.columns = ['Source', 'Count']
fig_vol = px.bar(vol_stats, y='Source', x='Count', orientation='h', color_discrete_sequence=['#0055FF'])
fig_vol.update_layout(**layout_defaults)

# 2. Contract Types
contracts = intel.get_contract_split()
fig_cont = px.pie(
    values=list(contracts.values()), 
    names=list(contracts.keys()), 
    hole=0.6, 
    color_discrete_sequence=['#0055FF', '#333333', '#999999', '#CCCCCC'] 
)
fig_cont.update_layout(**layout_defaults)

# 3. Tech Stack Gap
stack = intel.get_tech_stack_lag().reset_index()
stack.columns = ['Status', 'Count']
all_cats = pd.DataFrame({'Status': ['Modern', 'Stable', 'Dinosaur']})
stack = all_cats.merge(stack, on='Status', how='left').fillna(0)
fig_tech = px.bar(stack, x="Count", y="Status", color="Status", 
                 color_discrete_map={"Modern": "#0055FF", "Stable": "#999999", "Dinosaur": "#333333"})
fig_tech.update_layout(**layout_defaults)

# 4. Salary by Platform
plat_stats = df[df['avg_salary'] > 0].groupby('source')['avg_salary'].median().sort_values(ascending=True).reset_index()
plat_stats.columns = ['Source', 'Median Salary']
fig_sal = px.bar(plat_stats, y='Source', x='Median Salary', orientation='h', color_discrete_sequence=['#111'])
fig_sal.update_layout(**layout_defaults)

# 5. Top Innovators
modern_df = df[df['tech_status'] == 'Modern']
top_innovators = modern_df.groupby('company').agg(
    count=('hash', 'count'),
    avg_sal=('avg_salary', lambda x: x[x>0].median())
).sort_values('count', ascending=False).head(10)

innovators = []
for company, row in top_innovators.iterrows():
    sal_display = f"{int(row['avg_sal']/1000)}k" if pd.notna(row['avg_sal']) and row['avg_sal'] > 0 else "N/A"
    innovators.append({
        "company": company,
        "count": row['count'],
        "avg_sal": sal_display
    })

# --- RENDER ---
env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template('report.html')

output_html = template.render(
    date=datetime.date.today().strftime("%d. %B %Y"),
    total_jobs=len(df),
    med_salary=med_sal_fmt,
    tech_premium=tech_premium,
    en_share=en_share,
    innovators=innovators,
    json_source=fig_vol.to_json(),
    json_contract=fig_cont.to_json(),
    json_tech=fig_tech.to_json(),
    json_salary=fig_sal.to_json()
)

os.makedirs("public", exist_ok=True)
with open("public/index.html", "w", encoding="utf-8") as f:
    f.write(output_html)

print("Static report generated: public/index.html")