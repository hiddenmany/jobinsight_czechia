import streamlit as st
import pandas as pd
import altair as alt
import subprocess
import analyzer

# --- SWISS DESIGN CONFIG ---
st.set_page_config(page_title="Market Pulse // 2026", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
        background-color: #ffffff;
        color: #111111;
    }
    
    /* Stark Header */
    .header {
        font-size: 96px;
        font-weight: 800;
        letter-spacing: -4px;
        line-height: 0.9;
        margin-bottom: 60px;
        color: #111;
    }
    .header span { color: #0055FF; }
    
    /* Modular KPI */
    .kpi-box {
        border-top: 3px solid #111;
        padding-top: 15px;
        margin-bottom: 40px;
        transition: all 0.3s ease;
    }
    .kpi-box:hover { border-color: #0055FF; }
    
    .kpi-val { 
        font-family: 'JetBrains Mono', monospace; 
        font-size: 36px; 
        font-weight: 700; 
        color: #111;
    }
    .kpi-lab { 
        font-size: 12px; 
        text-transform: uppercase; 
        font-weight: 600;
        letter-spacing: 1px; 
        color: #666; 
        margin-top: 5px;
    }

    /* Tables */
    .stDataFrame { border: none !important; }
    
    /* Remove noise */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- ENGINE ---
@st.cache_resource(ttl=600)
def load_intel():
    return analyzer.MarketIntelligence()

intel = load_intel()
df = intel.df

# --- TOP SECTION ---
st.markdown('<div class="header">Market<br><span>Pulse.</span></div>', unsafe_allow_html=True)

if df.empty:
    st.warning("SYSTEM OFFLINE // NO DATA DETECTED")
    if st.button("EXECUTE SCRAPE"):
        try:
            result = subprocess.run(
                ["python", "scraper.py"],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            if result.returncode != 0:
                st.error(f"Scraper failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            st.error("Scraper timed out after 10 minutes")
        except Exception as e:
            st.error(f"Failed to run scraper: {e}")
        st.rerun()
    st.stop()

# --- KPI STRIP ---
cols = st.columns(5)
metrics = [
    ("Signals", len(df)),
    ("Median CZK", f"{int(df[df['avg_salary']>0]['avg_salary'].median()/1000)}k" if not df[df['avg_salary']>0].empty else "N/A"),
    ("English %", f"{int(intel.get_language_barrier()['English Friendly'] / len(df) * 100)}%"),
    ("Remote %", f"{int(intel.get_remote_truth()['True Remote'] / len(df) * 100)}%"),
    ("Stability", f"{int(intel.get_contract_split()['HPP'] / len(df) * 100)}%")
]

for i, (label, val) in enumerate(metrics):
    with cols[i]:
        st.markdown(f'<div class="kpi-box"><div class="kpi-val">{val}</div><div class="kpi-lab">{label}</div></div>', unsafe_allow_html=True)

st.markdown("---")

# --- ANALYTICAL GRID ---
c1, c2 = st.columns([1, 1])

with c1:
    st.markdown("### // GEOGRAPHIC VOLUME")
    geo_data = df['city'].value_counts().reset_index().head(10)
    # Highlight the top city with Blue, others Gray
    geo_data['color'] = ['#0055FF' if i == 0 else '#E0E0E0' for i in range(len(geo_data))]
    
    chart = alt.Chart(geo_data).mark_bar().encode(
        x=alt.X('count:Q', title=None),
        y=alt.Y('city:N', sort='-x', title=None),
        color=alt.Color('color:N', scale=None, legend=None)
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

    st.markdown("### // HUB BENCHMARKING")
    reg_stats = intel.get_regional_stats()
    reg_chart = alt.Chart(reg_stats).mark_bar(color='#0055FF').encode(
        x=alt.X('Median Salary:Q', title="Median Salary (CZK)"),
        y=alt.Y('Region:N', sort='-x', title=None),
        tooltip=['Region', 'Median Salary', 'Job Count']
    ).properties(height=200)
    st.altair_chart(reg_chart, use_container_width=True)
    
    reg_trends = intel.get_regional_trends()
    if not reg_trends.empty:
        st.markdown("**Regional Salary Movement**")
        st.dataframe(reg_trends, hide_index=True, use_container_width=True)

    st.markdown("### // BENEFIT SATURATION")
    benefits = ['multisport', 'sick day', 'flexibil', 'home office', 'akademie', 'stravenk']
    # Vectorized approach: O(n*m) instead of O(n²)
    ben_stats = []
    for benefit in benefits:
        count = df['description'].fillna('').str.lower().str.contains(benefit, regex=False).sum()
        ben_stats.append({"Benefit": benefit, "Signal": count})
    ben_stats = pd.DataFrame(ben_stats).sort_values('Signal', ascending=False)
    st.dataframe(ben_stats, hide_index=True, use_container_width=True)

with c2:
    st.markdown("### // CONTRACT REALITY")
    contracts = pd.DataFrame(list(intel.get_contract_split().items()), columns=['Type', 'Count'])
    # Distinct Palette: Blue, Dark Gray, Light Gray
    pie = alt.Chart(contracts).mark_arc(innerRadius=60).encode(
        theta=alt.Theta(field="Count", type="quantitative"),
        color=alt.Color(field="Type", type="nominal", scale=alt.Scale(range=['#0055FF', '#333333', '#CCCCCC'])),
        tooltip=['Type', 'Count']
    ).properties(height=300)
    st.altair_chart(pie, use_container_width=True)

    st.markdown("### // MARKET VIBE")
    vibe = intel.get_market_vibe().reset_index()
    vibe.columns = ['Metric', 'Intensity']
    vibe_chart = alt.Chart(vibe).mark_bar(color='#0055FF').encode(
        x=alt.X('Intensity:Q', title=None),
        y=alt.Y('Metric:N', sort='-x', title=None),
        tooltip=['Metric', 'Intensity']
    ).properties(height=150)
    st.altair_chart(vibe_chart, use_container_width=True)

st.markdown("---")
st.caption("JobsCzInsight v18.0 // Production Ready // Swiss Design System 2.0")