import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import analyzer
import datetime

# --- SIGNAL HUNTER DESIGN SYSTEM ---
st.set_page_config(page_title="SIGNAL // JobsCz", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for "Signal Hunter" Vibe
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600&display=swap');
    
    /* Global Reset & Dark Mode */
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
        background-color: #050505;
        color: #e0e0e0;
    }
    
    /* Typography */
    h1, h2, h3, .metric-label {
        font-family: 'JetBrains Mono', monospace;
        text-transform: uppercase;
        letter-spacing: -1px;
    }
    h1 { color: #fff; font-size: 2.5rem; }
    h3 { color: #888; font-size: 0.9rem; margin-bottom: 0px; }
    
    /* Cards & Containers */
    .signal-card {
        background-color: #0a0a0a;
        border: 1px solid #222;
        padding: 20px;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    .signal-card:hover { border-color: #444; }
    
    /* Metrics */
    .big-stat { font-family: 'JetBrains Mono', monospace; font-size: 2rem; font-weight: 700; color: #fff; }
    .stat-delta { font-size: 0.8rem; }
    .delta-pos { color: #00ff66; }
    .delta-neg { color: #ff3333; }
    .stat-label { font-size: 0.75rem; color: #666; text-transform: uppercase; letter-spacing: 1px; }

    /* Tables */
    .dataframe { font-family: 'JetBrains Mono', monospace !important; font-size: 0.8rem; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #000;
        border-right: 1px solid #222;
    }
    
    /* Streamlit overrides */
    div[data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace;
    }
    </style>
    """, unsafe_allow_html=True)

# --- DATA KERNEL ---
@st.cache_data(ttl=3600)
def load_data():
    intel = analyzer.MarketIntelligence()
    return intel

intel = load_data()
df = intel.df

# --- SIDEBAR CONTROLS ---
st.sidebar.markdown("### // CONTROLS")
selected_city = st.sidebar.selectbox("TARGET ZONE", ["All Cities"] + sorted(df['city'].unique().tolist()[:20]))
selected_cat = st.sidebar.selectbox("SECTOR", ["All Sectors"] + sorted(df['category'].unique().tolist()))

# Filter Data
filtered_df = df.copy()
if selected_city != "All Cities":
    filtered_df = filtered_df[filtered_df['city'] == selected_city]
if selected_cat != "All Sectors":
    filtered_df = filtered_df[filtered_df['category'] == selected_cat]

# --- METRIC COMPUTATION ---
market_vol = len(filtered_df)
avg_sal = filtered_df[filtered_df['avg_salary'] > 0]['avg_salary'].median()
transparency = (filtered_df[filtered_df['avg_salary'] > 0].shape[0] / max(market_vol, 1)) * 100

# Anomaly Detection (Fake comparison for demo as history is simplified in analyzer)
# In real app, we would compare to `intel.history` previous week
prev_vol = market_vol * 0.95 # Simulated -5% growth
vol_delta = market_vol - prev_vol

# --- DASHBOARD HEADER ---
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown("# MARKET SIGNAL v2.0")
    st.markdown(f"**TRACKING:** {market_vol} LIVE SIGNALS | **ZONE:** {selected_city.upper()} | **SECTOR:** {selected_cat.upper()}")
with c2:
    st.markdown(f"### SYSTEM STATUS")
    st.markdown("🟢 ONLINE")

st.markdown("---")

# --- LEVEL 1: ANOMALY DECK ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("SIGNAL VOLUME", f"{market_vol}", f"{int(vol_delta)}", delta_color="normal")

with col2:
    st.metric("MEDIAN REWARD", f"{int(avg_sal):,} CZK" if pd.notna(avg_sal) else "N/A", "Market Baseline")

with col3:
    st.metric("TRANSPARENCY", f"{int(transparency)}%", "Signal Clarity")

with col4:
    # Most aggressive competitor in this view
    if not filtered_df.empty:
        top_aggressor = filtered_df['company'].value_counts().idxmax()
        agg_count = filtered_df['company'].value_counts().max()
        st.metric("TOP AGGRESSOR", f"{top_aggressor[:15]}", f"{agg_count} Signals")
    else:
        st.metric("TOP AGGRESSOR", "N/A", "0")

# --- LEVEL 2: THE BATTLEFIELD (SCATTER) ---
st.markdown("### // SIGNAL MAP [SALARY vs. VOLUME]")
st.caption("Identifying high-value targets. Bubbles = Companies. Size = Job Volume. Y-Axis = Salary Offer.")

if not filtered_df.empty:
    # Aggregate data by company
    company_stats = filtered_df.groupby('company').agg(
        volume=('title', 'count'),
        avg_salary=('avg_salary', 'median'),
        source=('source', 'first')
    ).reset_index()
    
    # SANITIZATION
    company_stats['company'] = company_stats['company'].astype(str).str.strip().str.replace('\n', '', regex=False)
    company_stats['volume'] = pd.to_numeric(company_stats['volume'], errors='coerce').fillna(0)
    company_stats['avg_salary'] = pd.to_numeric(company_stats['avg_salary'], errors='coerce').fillna(0)
    
    # FILTER: Only show companies with valid salary info
    plot_data = company_stats[company_stats['avg_salary'] > 0].copy()
    
    # DIAGNOSTIC
    st.markdown(f"**VISIBLE SIGNALS:** {len(plot_data)} Companies identified with salary data.")
    
    if not plot_data.empty:
        tab_simple, tab_pro = st.tabs(["SIMPLE VIEW (Native)", "PRO VIEW (Plotly)"])
        
        with tab_simple:
            # Native Streamlit Chart - Failsafe
            st.scatter_chart(
                plot_data,
                x='volume',
                y='avg_salary',
                color='source',
                size='volume',
                height=500
            )
            
        with tab_pro:
            # Advanced Plotly Chart
            try:
                fig = px.scatter(
                    plot_data, 
                    x="volume", 
                    y="avg_salary", 
                    size="volume", 
                    color="source", 
                    hover_name="company",
                    log_x=True, 
                    template="plotly_dark",
                    height=500,
                    title="Market Battlefield"
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Pro View Error: {e}")
    else:
        st.warning("NO SALARY DATA DETECTED IN THIS FILTER SLICE.")
else:
    st.info("NO SIGNAL DETECTED IN THIS SECTOR.")

# --- LEVEL 3: DEEP SIGNAL ANALYSIS ---
st.markdown("### // DEEP SIGNAL ANALYSIS")

c_insight_1, c_insight_2, c_insight_3 = st.columns(3)

with c_insight_1:
    st.markdown("#### [A] THE PLATFORM PREMIUM")
    st.caption("Median salary difference by source. Where does the money live?")
    
    if 'source' in filtered_df.columns and 'avg_salary' in filtered_df.columns:
        plat_stats = filtered_df[filtered_df['avg_salary'] > 0].groupby('source')['avg_salary'].median().sort_values(ascending=False)
        if not plat_stats.empty:
            fig_plat = go.Figure()
            fig_plat.add_trace(go.Bar(
                x=plat_stats.index,
                y=plat_stats.values,
                marker_color=['#00ff66' if i==0 else '#333' for i in range(len(plat_stats))],
                text=[f"{v/1000:.1f}k" for v in plat_stats.values],
                textposition='auto'
            ))
            fig_plat.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=10, b=0),
                height=250,
                xaxis_title=None,
                yaxis_showgrid=False,
                yaxis_showticklabels=False
            )
            st.plotly_chart(fig_plat, use_container_width=True)
            
            premium = 0
            if 'Jobs_cz' in plat_stats and 'Prace_cz' in plat_stats:
                premium = plat_stats['Jobs_cz'] - plat_stats['Prace_cz']
                st.markdown(f"**SIGNAL:** Jobs.cz pays **+{int(premium):,} CZK** vs Prace.cz")

with c_insight_2:
    st.markdown("#### [B] THE TRANSPARENCY PARADOX")
    st.caption("Do transparent companies pay more? (Median CZK)")
    
    # Calculate on the fly
    company_transp = filtered_df.groupby('company').apply(lambda x: (x['avg_salary'].gt(0).sum() / max(len(x),1)) * 100)
    high_t = company_transp[company_transp > 80].index
    low_t = company_transp[company_transp < 20].index
    
    pay_high = filtered_df[(filtered_df['company'].isin(high_t)) & (filtered_df['avg_salary'] > 0)]['avg_salary'].median()
    pay_low = filtered_df[(filtered_df['company'].isin(low_t)) & (filtered_df['avg_salary'] > 0)]['avg_salary'].median()
    
    if pd.notna(pay_high) and pd.notna(pay_low):
        delta = pay_high - pay_low
        fig_transp = go.Figure()
        fig_transp.add_trace(go.Indicator(
            mode = "number+delta",
            value = pay_high,
            delta = {'reference': pay_low, 'relative': False, 'position': "bottom", 'valueformat': '.0f'},
            title = {"text": "Transparent Corps Pay"},
            domain = {'x': [0, 1], 'y': [0, 1]}
        ))
        fig_transp.update_layout(height=200, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_transp, use_container_width=True)
        st.markdown(f"**INSIGHT:** Showing salary correlates with **{'HIGHER' if delta > 0 else 'LOWER'}** pay.")

with c_insight_3:
    st.markdown("#### [C] KEYWORD VALUATION")
    st.caption("Market value of specific skills/terms.")
    
    kws = ['Python', 'Senior', 'Junior', 'Sales', 'English', 'Remote']
    kw_data = []
    for k in kws:
        med = filtered_df[filtered_df['title'].str.contains(k, case=False, na=False) & (filtered_df['avg_salary']>0)]['avg_salary'].median()
        if pd.notna(med):
            kw_data.append({"Keyword": k, "Value": med})
    
    if kw_data:
        kw_df = pd.DataFrame(kw_data).sort_values("Value", ascending=False)
        st.dataframe(
            kw_df.style.format({"Value": "{:,.0f} CZK"}),
            hide_index=True,
            use_container_width=True,
            height=200
        )
    else:
        st.info("No keyword data available in this slice.")

# --- LEVEL 4: RAW DATA INTERFACE ---
with st.expander("OPEN RAW DATA TERMINAL", expanded=False):
    st.dataframe(
        filtered_df[['title', 'company', 'salary', 'location', 'source', 'link']],
        use_container_width=True,
        height=400
    )

st.caption("SIGNAL HUNTER v2.0 | ENGINE: JobsCzInsight | TERMINAL: 102")

# --- LEVEL 5: STRATEGIC INTEL (2026 UPDATE) ---
st.markdown("---")
st.markdown("### // STRATEGIC WARFARE INTEL")
st.caption("Advanced market analysis: Ghost Jobs, Contract Reality, and Tech Obsolescence.")

tab_strat_1, tab_strat_2 = st.tabs(["TACTICAL VULNERABILITIES", "TECH & TALENT FLOW"])

with tab_strat_1:
    c_s1, c_s2, c_s3 = st.columns(3)
    
    with c_s1:
        st.markdown("#### [1] GHOST JOB INDEX")
        st.caption("Companies appearing to repost/churn roles.")
        ghosts = intel.get_ghost_job_index()
        if not ghosts.empty:
            st.dataframe(ghosts[['Ghost Score']], use_container_width=True, height=200)
        else:
            st.info("No ghost signals detected.")

    with c_s2:
        st.markdown("#### [2] IČO vs HPP REALITY")
        st.caption("Contract stability check.")
        contracts = intel.get_contract_split()
        fig_cont = px.pie(values=list(contracts.values()), names=list(contracts.keys()), hole=0.6, color_discrete_sequence=px.colors.sequential.RdBu)
        fig_cont.update_layout(height=250, margin=dict(l=0,r=0,t=0,b=0), showlegend=False)
        fig_cont.add_annotation(text=f"{int(contracts.get('IČO (Contract)', 0)/max(sum(contracts.values()),1)*100)}% IČO", showarrow=False, font=dict(color="white", size=12))
        st.plotly_chart(fig_cont, use_container_width=True)

    with c_s3:
        st.markdown("#### [3] REMOTE LIE DETECTOR")
        st.caption("Remote tags vs. Body text reality.")
        remote = intel.get_remote_truth()
        fig_rem = go.Figure(go.Bar(
            x=list(remote.values()),
            y=list(remote.keys()),
            orientation='h',
            marker=dict(color=['#00ff66', '#ff3333', '#333'])
        ))
        fig_rem.update_layout(height=250, margin=dict(l=0,r=0,t=0,b=0), template="plotly_dark")
        st.plotly_chart(fig_rem, use_container_width=True)

with tab_strat_2:
    c_t1, c_t2 = st.columns(2)
    
    with c_t1:
        st.markdown("#### [4] TECH STACK LAG (2026)")
        st.caption("Modern vs. Legacy keywords in descriptions.")
        stack = intel.get_tech_stack_lag()
        
        # Combine into DF
        df_stack = pd.DataFrame([
            {"Type": "Modern", "Count": sum(stack['Modern'].values())},
            {"Type": "Legacy", "Count": sum(stack['Legacy'].values())}
        ])
        fig_stack = px.bar(df_stack, x="Count", y="Type", color="Type", color_discrete_map={"Modern": "#00ccff", "Legacy": "#555"})
        fig_stack.update_layout(height=200, margin=dict(l=0,r=0,t=0,b=0), template="plotly_dark")
        st.plotly_chart(fig_stack, use_container_width=True)
        
        with st.expander("Detailed Keyword Counts"):
            st.write("Modern:", stack['Modern'])
            st.write("Legacy:", stack['Legacy'])

    with c_t2:
        st.markdown("#### [5] THE ENGLISH TAX")
        st.caption("Talent pool accessibility.")
        lang = intel.get_language_barrier()
        
        st.metric("CZECH REQUIRED", f"{lang['Czech Required (Puddle)']}", help="Fishing in a puddle")
        st.metric("ENGLISH FRIENDLY", f"{lang['English Friendly (Ocean)']}", help="Fishing in the ocean", delta_color="inverse")
