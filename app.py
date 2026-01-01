import streamlit as st
import pandas as pd
import plotly.express as px
import analyzer
import os

# --- SWISS DESIGN SYSTEM (MINIMALIST) ---
st.set_page_config(page_title="Market Overview // 2026", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
        background-color: #ffffff;
        color: #000000;
    }
    
    /* Header */
    .header-text {
        font-size: 80px;
        font-weight: 700;
        letter-spacing: -4px;
        line-height: 0.9;
        margin-bottom: 20px;
        color: #000;
    }
    
    .sub-header {
        font-size: 18px;
        font-weight: 400;
        color: #666;
        margin-bottom: 60px;
        border-top: 1px solid #000;
        padding-top: 10px;
        width: 300px;
    }

    /* KPI Cards */
    .kpi-card {
        border-left: 4px solid #000;
        padding-left: 20px;
        margin-bottom: 40px;
    }
    .kpi-value {
        font-size: 48px;
        font-weight: 700;
        line-height: 1;
    }
    .kpi-label {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #888;
    }

    /* Minimalist Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #f9f9f9;
        border-right: 1px solid #eee;
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- DATA KERNEL ---
@st.cache_data(ttl=3600)
def get_intel():
    return analyzer.MarketIntelligence()

intel = get_intel()
df = intel.df

# --- HEADER ---
st.markdown('<div class="header-text">Job Market<br>Snapshot</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Czechia // Q1 2026<br>Analytical Intelligence</div>', unsafe_allow_html=True)

if df.empty:
    st.error("No data found. Please run the scraper.")
    st.stop()

# --- TOP KPI LINE ---
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-value">{len(df)}</div><div class="kpi-label">Active Signals</div></div>', unsafe_allow_html=True)
with c2:
    med_sal = df[df['avg_salary']>0]['avg_salary'].median()
    st.markdown(f'<div class="kpi-card"><div class="kpi-value">{int(med_sal/1000) if pd.notna(med_sal) else "N/A"}k</div><div class="kpi-label">Median Wage (CZK)</div></div>', unsafe_allow_html=True)
with c3:
    en_share = int(intel.get_language_barrier()['English Friendly (Ocean)'] / len(df) * 100)
    st.markdown(f'<div class="kpi-card"><div class="kpi-value">{en_share}%</div><div class="kpi-label">English Adoption</div></div>', unsafe_allow_html=True)
with c4:
    remote_share = int(intel.get_remote_truth()['True Remote'] / len(df) * 100)
    st.markdown(f'<div class="kpi-card"><div class="kpi-value">{remote_share}%</div><div class="kpi-label">True Remote</div></div>', unsafe_allow_html=True)

st.markdown("---")

# --- TRENDS & ANALYSIS ---
col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown("### 01 // Platform Distribution")
    vol_stats = df['source'].value_counts()
    fig_vol = px.bar(vol_stats, orientation='h', color_discrete_sequence=['#000'])
    fig_vol.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis_visible=False,
        yaxis_title=None,
        showlegend=False,
        margin=dict(l=0,r=0,t=0,b=0),
        height=300
    )
    st.plotly_chart(fig_vol, use_container_width=True)

    st.markdown("### 02 // Common Benefits")
    benefits_kws = ['stravenk', 'multisport', 'sick day', 'flexibil', 'home office', 'akademie', 'vzdělávání', 'notebook', 'telefon', 'psí']
    desc_all = " ".join(df['description'].fillna('').astype(str)).lower()
    ben_counts = {k: desc_all.count(k) for k in benefits_kws}
    df_ben = pd.DataFrame(list(ben_counts.items()), columns=['Benefit', 'Count']).sort_values('Count', ascending=False)
    st.dataframe(df_ben, hide_index=True, use_container_width=True)

with col_right:
    st.markdown("### 03 // JD Writing Trends")
    # Length analysis
    df['jd_len'] = df['description'].fillna('').apply(len)
    avg_len = int(df['jd_len'].mean())
    
    st.markdown(f"**Average Description Length:** {avg_len} characters")
    
    # Contract focus
    contracts = intel.get_contract_split()
    fig_cont = px.pie(values=list(contracts.values()), names=list(contracts.keys()), color_discrete_sequence=['#000', '#666', '#ccc', '#eee'])
    fig_cont.update_layout(height=300, showlegend=True, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig_cont, use_container_width=True)

    st.markdown("### 04 // Market Sentiment")
    vibe = intel.get_market_vibe()
    st.dataframe(vibe, use_container_width=True)

st.markdown("---")
st.caption("Data Source: Jobs.cz, Prace.cz, WTTJ, StartupJobs, Cocuma, LinkedIn. Refreshed: 2026-01-01.")
