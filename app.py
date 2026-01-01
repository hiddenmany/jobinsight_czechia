import streamlit as st
import pandas as pd
import altair as alt
import analyzer
import os

# --- SWISS DESIGN CONFIG ---
st.set_page_config(page_title="Market Pulse // 2026", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700&family=JetBrains+Mono:wght@400&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
        background-color: #ffffff;
        color: #000000;
    }
    
    /* Stark Header */
    .header {
        font-size: 120px;
        font-weight: 700;
        letter-spacing: -8px;
        line-height: 0.8;
        margin-bottom: 40px;
        color: #000;
    }
    
    /* Modular KPI */
    .kpi-box {
        border-top: 2px solid #000;
        padding-top: 10px;
        margin-bottom: 30px;
    }
    .kpi-val { font-family: 'JetBrains Mono', monospace; font-size: 42px; font-weight: 700; }
    .kpi-lab { font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: #666; }

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
st.markdown('<div class="header">Market<br>Pulse.</div>', unsafe_allow_html=True)

if df.empty:
    st.warning("SYSTEM OFFLINE // NO DATA DETECTED")
    if st.button("EXECUTE SCRAPE"):
        os.system("python scraper.py")
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
    chart = alt.Chart(geo_data).mark_bar(color='#000').encode(
        x=alt.X('count:Q', title=None),
        y=alt.Y('city:N', sort='-x', title=None),
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

    st.markdown("### // BENEFIT SATURATION")
    benefits = ['multisport', 'sick day', 'flexibil', 'home office', 'akademie', 'stravenk']
    desc_blob = " ".join(df['description'].fillna('').astype(str)).lower()
    ben_stats = pd.DataFrame([{"Benefit": b, "Signal": desc_blob.count(b)} for b in benefits]).sort_values('Signal', ascending=False)
    st.dataframe(ben_stats, hide_index=True, use_container_width=True)

with c2:
    st.markdown("### // CONTRACT REALITY")
    contracts = pd.DataFrame(list(intel.get_contract_split().items()), columns=['Type', 'Count'])
    pie = alt.Chart(contracts).mark_arc(innerRadius=50).encode(
        theta=alt.Theta(field="Count", type="quantitative"),
        color=alt.Color(field="Type", type="nominal", scale=alt.Scale(range=['#000', '#666', '#ccc'])),
    ).properties(height=300)
    st.altair_chart(pie, use_container_width=True)

    st.markdown("### // MARKET VIBE")
    vibe = intel.get_market_vibe().reset_index()
    vibe.columns = ['Metric', 'Intensity']
    vibe_chart = alt.Chart(vibe).mark_bar(color='#ff0000').encode(
        x=alt.X('Intensity:Q', title=None),
        y=alt.Y('Metric:N', sort='-x', title=None)
    ).properties(height=150)
    st.altair_chart(vibe_chart, use_container_width=True)

st.markdown("---")
st.caption("JobsCzInsight v15.0 // Production Ready // Swiss Design System")