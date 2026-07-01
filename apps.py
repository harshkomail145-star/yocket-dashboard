import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# ==========================================
# 1. PAGE CONFIG & MODERN THEME STYLING
# ==========================================
st.set_page_config(page_title="Fall 26 Analytics", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; border-top: 4px solid #4f46e5; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1); }
    .section-header { background-color: #ffffff; padding: 15px; border-radius: 8px; border-left: 5px solid #4f46e5; margin-top: 30px; margin-bottom: 15px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);}
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #e2e8f0; border-radius: 8px 8px 0 0; padding: 10px 20px; font-weight: 600;}
    .stTabs [aria-selected="true"] { background-color: #ffffff; border-bottom: 2px solid #4f46e5;}
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Fall 26 Command Center")

# ==========================================
# 2. THE LIVE DATA PIPELINE ENGINE
# ==========================================
@st.cache_data
def load_and_process_data(file):
    df = pd.read_csv(file)
    
    # 1. Standardize Dates
    date_cols = ['date_shared', 'login_date', 'sanction_date', 'pf_date']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
        
    # 2. Calculate TAT (Turnaround Time in Days)
    df['tat_bp_login'] = (df['login_date'] - df['date_shared']).dt.days
    df['tat_login_sanc'] = (df['sanction_date'] - df['login_date']).dt.days
    df['tat_sanc_pf'] = (df['pf_date'] - df['sanction_date']).dt.days
    
    # 3. Flight Risk Engine (Finds the max stage a student reached ANYWHERE across all banks)
    # Stage Hierarchy: 1=BP, 2=Login, 3=Sanction, 4=PF
    df['stage_val'] = 0
    df.loc[df['date_shared'].notnull(), 'stage_val'] = 1
    df.loc[df['login_date'].notnull(), 'stage_val'] = 2
    df.loc[df['sanction_date'].notnull(), 'stage_val'] = 3
    df.loc[df['pf_date'].notnull(), 'stage_val'] = 4
    
    # Map the absolute maximum stage back to every row for that user
    user_max_stage = df.groupby('user_id')['stage_val'].max()
    df['user_max_stage'] = df['user_id'].map(user_max_stage)
    
    return df

# ==========================================
# 3. GLOBAL FILTERS (SIDEBAR)
# ==========================================
with st.sidebar:
    st.header("⚙️ Global Controls")
    
    uploaded_file = st.file_uploader("Upload Yocket Lead CSV", type=["csv"])
    
    if uploaded_file is None:
        st.warning("⚠️ Waiting for data... Please upload your CSV to activate the dashboard.")
        st.stop() # Halts app until data is loaded
        
    # Process the file via the engine
    raw_df = load_and_process_data(uploaded_file)
    
    # Dynamic Bank Filter based on live data
    available_banks = raw_df['bank_name'].dropna().unique().tolist()
    selected_banks = st.multiselect("Select Bank Partners", available_banks, default=available_banks)
    
    st.divider()
    st.caption("UI Mode: LIVE PANDAS ENGINE 🟢")

# ------------------------------------------
# CREATE OUR TWO MASTER DATAFRAMES
# ------------------------------------------
# 1. Global Filtered DF (For Tab 1 YoY Date-Logic)
df = raw_df[raw_df['bank_name'].isin(selected_banks)].copy()

# 2. Cohort Filtered DF (For Tab 2, 3, 4 Micro-Funnels)
df_cohort = df[df['cohort'] == 'Fall 26'].copy()

# Initialize our Top-Level Navigational Tabs
tab_overall, tab_bp_login, tab_log_san, tab_san_pf = st.tabs([
    "🌐 Overall Performance", 
    "🔍 BP to Login",
    "📝 Login to Sanction",
    "✅ Sanction to PF"
])

# ==========================================
# TAB 1: OVERALL PERFORMANCE (DATE-DRIVEN)
# ==========================================
with tab_overall:
    st.markdown('<div class="section-header"><h2>📈 1. Y-o-Y Performance & Monthly Logins</h2></div>', unsafe_allow_html=True)

    # --- TAB 1 YTD DATE LOGIC ---
    today = pd.to_datetime('today')
    f26_start = pd.to_datetime(f"{today.year}-01-01")
    f25_start = pd.to_datetime(f"{today.year - 1}-01-01")
    f25_end = today.replace(year=today.year - 1)

    def count_ytd(dataframe, date_col, start_dt, end_dt):
        return ((dataframe[date_col] >= start_dt) & (dataframe[date_col] <= end_dt)).sum()

    fall_26_data = [
        count_ytd(df, 'date_shared', f26_start, today),
        count_ytd(df, 'login_date', f26_start, today),
        count_ytd(df, 'sanction_date', f26_start, today),
        count_ytd(df, 'pf_date', f26_start, today)
    ]
    
    fall_25_data = [
        count_ytd(df, 'date_shared', f25_start, f25_end),
        count_ytd(df, 'login_date', f25_start, f25_end),
        count_ytd(df, 'sanction_date', f25_start, f25_end),
        count_ytd(df, 'pf_date', f25_start, f25_end)
    ]
    
    yoy_growth = []
    for f26, f25 in zip(fall_26_data, fall_25_data):
        if f25 > 0:
            growth = ((f26 - f25) / f25) * 100
            yoy_growth.append(f"+{growth:.1f}%" if growth >= 0 else f"{growth:.1f}%")
        else:
            yoy_growth.append("N/A")

    col1, col2 = st.columns(2)
    COLOR_FALL_26 = "#1e40af" 
    COLOR_FALL_25 = "#93c5fd" 

    with col1:
        st.subheader("Y-o-Y Metrics (YTD Comparison)")
        stages = ['Shared', 'Login', 'Sanction', 'PF']
        
        fig_top_metrics = go.Figure()
        fig_top_metrics.add_trace(go.Bar(name="Fall '26", x=stages, y=fall_26_data, marker_color=COLOR_FALL_26, text=fall_26_data, textposition='outside', textfont=dict(size=14, color='black')))
        fig_top_metrics.add_trace(go.Bar(name="Fall '25", x=stages, y=fall_25_data, marker_color=COLOR_FALL_25, text=fall_25_data, textposition='outside', textfont=dict(size=14, color='black')))

        growth_annotations = []
        for i, stage in enumerate(stages):
            y_max = max(fall_25_data[i], fall_26_data[i])
            icon = "⬇" if "-" in yoy_growth[i] else "⬆"
            growth_annotations.append(dict(
                x=stage, y=y_max + (y_max * 0.15) if y_max > 0 else 10, 
                text=f"<b>{icon} {yoy_growth[i]}</b><br><span style='font-size:11px'>YoY Growth</span>",
                showarrow=False, font=dict(size=14, color="black"), bgcolor="#f8fafc", bordercolor="#94a3b8", borderwidth=1, borderpad=6
            ))

        fig_top_metrics.update_layout(barmode='group', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5), annotations=growth_annotations, margin=dict(t=80))
        fig_top_metrics.update_yaxes(showgrid=True, gridcolor='#e2e8f0')
        st.plotly_chart(fig_top_metrics, use_container_width=True)

    with col2:
        st.subheader("YoY Monthly Logins")
        st.info("Live Monthly extraction grouped by `df['login_date'].dt.month` goes here.")
    
    st.divider()

    # --- TAB 1 BOTTOM: COHORT FUNNEL ---
    st.markdown('<div class="section-header"><h2>🧬 3. Shared Leads Pipeline (Fall 26 Cohort)</h2></div>', unsafe_allow_html=True)
    st.markdown("Tracking active volumes and drop-offs strictly for leads tagged **Fall 26**.")
    
    # Cohort-driven totals
    tot_shared = df_cohort['date_shared'].notnull().sum()
    tot_login = df_cohort['login_date'].notnull().sum()
    tot_sanc = df_cohort['sanction_date'].notnull().sum()
    tot_pf = df_cohort['pf_date'].notnull().sum()
    totals = [tot_shared, tot_login, tot_sanc, tot_pf]
    
    # Active Counts
    curr_bp = df_cohort[df_cohort['lender_stage'] == 'Bank Prospect'].shape[0]
    curr_log = df_cohort[df_cohort['lender_stage'] == 'Login'].shape[0]
    curr_san = df_cohort[df_cohort['lender_stage'] == 'Sanction'].shape[0]
    currents = [curr_bp, curr_log, curr_san, tot_pf] # PF is endpoint

    # Lost Counts
    lost_bp = df_cohort[df_cohort['lost_category'] == 'Lost from BP'].shape[0]
    lost_log = df_cohort[df_cohort['lost_category'] == 'Lost from Login'].shape[0]
    lost_san = df_cohort[df_cohort['lost_category'] == 'Lost from Sanction'].shape[0]
    losts = [lost_bp, lost_log, lost_san, 0]
    
    custom_text = [f"<b style='font-size: 32px; color: white;'>{v:,}</b>" for v in totals]
    
    fig_funnel = go.Figure(go.Funnel(
        orientation='v', x=stages, y=totals, text=custom_text, textposition="inside", textinfo="text",
        marker={"color": ["#4f46e5", "#6366f1", "#818cf8", "#a5b4fc"], "line": {"width": [2, 2, 2, 2], "color": ["white"]*4}},
        connector={"line": {"color": "#e2e8f0", "dash": "solid", "width": 2}, "fillcolor": "rgba(226, 232, 240, 0.4)"}
    ))
    
    for i, stage in enumerate(stages):
        if totals[i] > 0:
            top_y = (totals[i] / 2) * 0.70
            bottom_y = -(totals[i] / 2) * 0.70
            
            fig_funnel.add_annotation(x=stage, y=top_y, text=f"<span style='color:#a7f3d0; font-size:16px'>●</span> <b style='color:white; font-size:15px'>{currents[i]}</b>", showarrow=False, xanchor='right', xshift=-45)
            if losts[i] > 0:
                fig_funnel.add_annotation(x=stage, y=bottom_y, text=f"<span style='color:#fca5a5; font-size:16px'>●</span> <b style='color:white; font-size:15px'>{losts[i]}</b>", showarrow=False, xanchor='right', xshift=-45)

    # Dynamic Conversion Arrows
    bp_log_pct = (tot_login/tot_shared)*100 if tot_shared > 0 else 0
    log_san_pct = (tot_sanc/tot_login)*100 if tot_login > 0 else 0
    san_pf_pct = (tot_pf/tot_sanc)*100 if tot_sanc > 0 else 0
    
    fig_funnel.add_annotation(x=0.5, y=1.05, xref="x", yref="paper", text=f"<b>{bp_log_pct:.1f}% ➔</b>", showarrow=False, font=dict(size=14, color="#4f46e5"), bgcolor="#ffffff", bordercolor="#e2e8f0", borderwidth=1, borderpad=5)
    fig_funnel.add_annotation(x=1.5, y=1.05, xref="x", yref="paper", text=f"<b>{log_san_pct:.1f}% ➔</b>", showarrow=False, font=dict(size=14, color="#4f46e5"), bgcolor="#ffffff", bordercolor="#e2e8f0", borderwidth=1, borderpad=5)
    fig_funnel.add_annotation(x=2.5, y=1.05, xref="x", yref="paper", text=f"<b>{san_pf_pct:.1f}% ➔</b>", showarrow=False, font=dict(size=14, color="#4f46e5"), bgcolor="#ffffff", bordercolor="#e2e8f0", borderwidth=1, borderpad=5)
    
    fig_funnel.update_layout(height=400, margin={"t": 70, "b": 40, "l": 20, "r": 20}, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(showline=False, tickfont=dict(size=15, weight="bold", color="#1e293b")), yaxis=dict(showticklabels=False, showgrid=False))
    st.plotly_chart(fig_funnel, use_container_width=True)

# ==========================================
# TAB 2: BP TO LOGIN DEEP DIVE (COHORT-DRIVEN)
# ==========================================
with tab_bp_login:
    # --- DYNAMIC DATA PREP FOR BP ---
    bp_df = df_cohort[df_cohort['date_shared'].notnull()]
    
    # 1. Top Branches by Volume
    branch_counts = bp_df['location'].value_counts()
    top_branches = branch_counts.head(5).index.tolist()
    
    if len(branch_counts) > 5:
        top_branches.append("Others")
        bp_vols = branch_counts.head(5).tolist() + [branch_counts.iloc[5:].sum()]
    else:
        bp_vols = branch_counts.tolist()
        
    total_bp_pie = sum(bp_vols) if sum(bp_vols) > 0 else 1
    bp_pcts = [f"{(v/total_bp_pie)*100:.1f}%" for v in bp_vols]
    
    # Ensure we only plot specific branches on the y-axes, not "Others"
    shared_y_branches = [b for b in top_branches if b != "Others"]

    # --- TOP CARDS: VOLUME DISTRIBUTION ---
    st.markdown('<div class="section-header"><h2>🗂️ BP Stage Lead Distribution</h2></div>', unsafe_allow_html=True)
    card_cols = st.columns(6)
    for i, col in enumerate(card_cols):
        if i < len(top_branches):
            with col:
                st.metric(label=f"📍 {top_branches[i]}", value=f"{bp_vols[i]:,} Leads", delta=f"{bp_pcts[i]} Share", delta_color="off")
    st.divider()

    # --- STAGE 1 LOGIC AGGREGATION ---
    conv_rates, tat_days, true_active_bp, paid_comp_bp = [], [], [], []
    bp_under_7, bp_over_7 = [], []
    bp_exclusive, bp_comp_login, bp_comp_sanc = [], [], []

    active_bp_df = bp_df[bp_df['lender_stage'] == 'Bank Prospect'].copy()
    active_bp_df['aging_days'] = (pd.to_datetime('today') - active_bp_df['date_shared']).dt.days

    for b in shared_y_branches:
        # Conversion & TAT
        b_df = bp_df[bp_df['location'] == b]
        shared_c = b_df.shape[0]
        log_c = b_df['login_date'].notnull().sum()
        conv_rates.append(round((log_c/shared_c)*100, 1) if shared_c > 0 else 0)
        tat_days.append(round(b_df['tat_bp_login'].mean(), 1) if not pd.isna(b_df['tat_bp_login'].mean()) else 0)
        
        # Flight Risk (Active)
        b_act = active_bp_df[active_bp_df['location'] == b]
        true_active_bp.append(b_act[b_act['user_max_stage'] < 4].shape[0]) # Not paid PF elsewhere
        paid_comp_bp.append(b_act[b_act['user_max_stage'] == 4].shape[0])  # Paid PF elsewhere
        
        # Aging
        bp_under_7.append(b_act[b_act['aging_days'] < 7].shape[0])
        bp_over_7.append(b_act[b_act['aging_days'] >= 7].shape[0])
        
        # Pipeline Spread
        bp_exclusive.append(b_act[b_act['user_max_stage'] == 1].shape[0])
        bp_comp_login.append(b_act[b_act['user_max_stage'] == 2].shape[0])
        bp_comp_sanc.append(b_act[b_act['user_max_stage'] == 3].shape[0])

    # --- SECTION 1: CONVERSION, AGING SLA & FLIGHT RISK ---
    st.markdown('<div class="section-header"><h2>📊 1. Conversion, Aging & Immediate Flight Risk</h2></div>', unsafe_allow_html=True)
    col_c1, col_c2, col_c3 = st.columns(3)
    
    with col_c1:
        nat_avg = round((df_cohort['login_date'].notnull().sum() / tot_shared)*100, 1) if tot_shared > 0 else 0
        st.markdown(f"<h4 style='text-align: center; color: #475569;'>BP ➔ Login Rate<br><span style='font-size:14px; font-weight:normal;'>(Nat. Avg: {nat_avg}%)</span></h4>", unsafe_allow_html=True)
        conv_colors = ["#9f1239" if val < nat_avg else "#cbd5e1" for val in conv_rates]
        fig_conv = go.Figure(go.Bar(y=shared_y_branches, x=conv_rates, orientation='h', marker_color=conv_colors, text=[f"{v}%" for v in conv_rates], textposition="inside", insidetextanchor="middle", textfont=dict(color=["white" if c == "#9f1239" else "#0f172a" for c in conv_colors], weight="bold")))
        fig_conv.add_vline(x=nat_avg, line_dash="dash", line_color="#475569", line_width=2)
        fig_conv.update_layout(height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569")))
        st.plotly_chart(fig_conv, use_container_width=True)

    with col_c2:
        target_tat = 3.0
        st.markdown(f"<h4 style='text-align: center; color: #475569;'>BP ➔ Login Stage TAT<br><span style='font-size:14px; font-weight:normal;'>(Target SLA: {target_tat} Days)</span></h4>", unsafe_allow_html=True)
        tat_colors = ["#9f1239" if val > target_tat else "#cbd5e1" for val in tat_days]
        fig_tat = go.Figure(go.Bar(y=shared_y_branches, x=tat_days, orientation='h', marker_color=tat_colors, text=[f"{v} days" for v in tat_days], textposition="inside", insidetextanchor="middle", textfont=dict(color=["white" if c == "#9f1239" else "#0f172a" for c in tat_colors], weight="bold")))
        fig_tat.add_vline(x=target_tat, line_dash="dash", line_color="#475569", line_width=2)
        fig_tat.update_layout(height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
        st.plotly_chart(fig_tat, use_container_width=True)

    with col_c3:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Active BP vs. Paid to Competitor<br><span style='font-size:14px; font-weight:normal;'><span style='color:#cbd5e1'>■</span> True Active BP &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#f97316'>■</span> Paid Competitor</span></h4>", unsafe_allow_html=True)
        paid_pcts = [f"({int((p/(a+p))*100)}%)" if (a+p)>0 else "(0%)" for a, p in zip(true_active_bp, paid_comp_bp)]
        fig_flight = go.Figure()
        fig_flight.add_trace(go.Bar(name="True Active BP", y=shared_y_branches, x=true_active_bp, orientation='h', marker_color="#e2e8f0", text=[v if v>0 else "" for v in true_active_bp], textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")))
        fig_flight.add_trace(go.Bar(name="Paid Competitor", y=shared_y_branches, x=paid_comp_bp, orientation='h', marker_color="#f97316", text=[f"{v} {pct}" if v>0 else "" for v, pct in zip(paid_comp_bp, paid_pcts)], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))
        fig_flight.update_layout(barmode="stack", height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"), showlegend=False)
        st.plotly_chart(fig_flight, use_container_width=True)
    st.divider()

    # --- TRUE WORKABLE BP LEADS BREAKDOWN ---
    st.subheader("🔎 True Workable BP Leads Breakdown")
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Active Leads Aging</h4>", unsafe_allow_html=True)
        fig_bp_aging = go.Figure()
        fig_bp_aging.add_trace(go.Bar(name="< 7 Days", y=shared_y_branches, x=bp_under_7, orientation='h', marker_color="#60a5fa", text=[f"{v}" if v > 0 else "" for v in bp_under_7], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))
        fig_bp_aging.add_trace(go.Bar(name="> 7 Days", y=shared_y_branches, x=bp_over_7, orientation='h', marker_color="#ef4444", text=[f"{v}" if v > 0 else "" for v in bp_over_7], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))
        fig_bp_aging.update_layout(barmode="stack", height=380, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569")))
        st.plotly_chart(fig_bp_aging, use_container_width=True)

    with col_w2:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Competitor Pipeline Spread</h4>", unsafe_allow_html=True)
        fig_bp_work = go.Figure()
        fig_bp_work.add_trace(go.Bar(name="Exclusive (Safe)", y=shared_y_branches, x=bp_exclusive, orientation='h', marker_color="#a7f3d0", text=[f"{v}" if v > 0 else "" for v in bp_exclusive], textposition="inside", insidetextanchor="middle", textfont=dict(color="#0f172a", weight="bold")))
        fig_bp_work.add_trace(go.Bar(name="⚠️ In Comp Login", y=shared_y_branches, x=bp_comp_login, orientation='h', marker_color="#fef08a", text=[f"{v}" if v > 0 else "" for v in bp_comp_login], textposition="inside", insidetextanchor="middle", textfont=dict(color="#854d0e", weight="bold")))
        fig_bp_work.add_trace(go.Bar(name="🚨 In Comp Sanction", y=shared_y_branches, x=bp_comp_sanc, orientation='h', marker_color="#fda4af", text=[f"{v}" if v > 0 else "" for v in bp_comp_sanc], textposition="inside", insidetextanchor="middle", textfont=dict(color="#881337", weight="bold")))
        fig_bp_work.update_layout(barmode="stack", height=380, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
        st.plotly_chart(fig_bp_work, use_container_width=True)
    st.divider()

    # --- SECTION 3: BP STAGE LOST ANALYSIS ---
    # Running the Flight Risk logic for leads entirely "Lost from BP"
    lost_bp_df = bp_df[bp_df['lost_category'] == 'Lost from BP']
    
    true_dead_lost, comp_log_lost, comp_san_lost, comp_pf_lost = [], [], [], []
    bp_leakage_pcts = []
    
    for b in shared_y_branches:
        # Leakage Rate Calculation
        total_shared_b = bp_df[bp_df['location'] == b].shape[0]
        total_lost_b = lost_bp_df[lost_bp_df['location'] == b].shape[0]
        bp_leakage_pcts.append(round((total_lost_b / total_shared_b)*100, 1) if total_shared_b > 0 else 0)
        
        # Flight Risk Distribution
        b_lost = lost_bp_df[lost_bp_df['location'] == b]
        true_dead_lost.append(b_lost[b_lost['user_max_stage'] == 1].shape[0])
        comp_log_lost.append(b_lost[b_lost['user_max_stage'] == 2].shape[0])
        comp_san_lost.append(b_lost[b_lost['user_max_stage'] == 3].shape[0])
        comp_pf_lost.append(b_lost[b_lost['user_max_stage'] == 4].shape[0])

    st.markdown('<div class="section-header"><h2>🚨 3. BP Stage Lost Analysis</h2></div>', unsafe_allow_html=True)
    col_l1, col_l2 = st.columns(2)

    with col_l1:
        st.markdown("<h4 style='text-align: center; color: #475569;'>BP Leakage Rate (% of Shared)<br><span style='font-size:13px; visibility:hidden;'>Invisible Spacer</span></h4>", unsafe_allow_html=True)
        leakage_colors = ["#9f1239" if p > 20 else ("#ef4444" if p > 13 else "#fca5a5") for p in bp_leakage_pcts]
        fig_bp_leakage = go.Figure(go.Bar(y=shared_y_branches, x=bp_leakage_pcts, orientation='h', marker_color=leakage_colors, text=[f"{p}%" for p in bp_leakage_pcts], textposition="inside", insidetextanchor="middle", textfont=dict(color=["white" if c in ["#9f1239", "#ef4444"] else "#0f172a" for c in leakage_colors], weight="bold")))
        fig_bp_leakage.update_layout(height=350, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569")))
        st.plotly_chart(fig_bp_leakage, use_container_width=True)

    with col_l2:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Competitor Pipeline Spread (Lost Leads)<br><span style='font-size:13px; font-weight:normal;'><span style='color:#e2e8f0'>■</span> True Dead &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#fdba74'>■</span> Comp Login &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#f97316'>■</span> Comp Sanction &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#9f1239'>■</span> Comp PF Paid</span></h4>", unsafe_allow_html=True)
        
        bp_lost_totals = [t + l + s + p for t, l, s, p in zip(true_dead_lost, comp_log_lost, comp_san_lost, comp_pf_lost)]
        bp_potential_loss_pcts = [f"{((tot - td) / tot) * 100:.1f}%" if tot > 0 else "0%" for tot, td in zip(bp_lost_totals, true_dead_lost)]

        fig_bp_lost_spread = go.Figure()
        fig_bp_lost_spread.add_trace(go.Bar(name="True Dead", y=shared_y_branches, x=true_dead_lost, orientation='h', marker_color="#e2e8f0", text=[f"{v}" if v > 0 else "" for v in true_dead_lost], textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")))
        fig_bp_lost_spread.add_trace(go.Bar(name="Comp Login", y=shared_y_branches, x=comp_log_lost, orientation='h', marker_color="#fdba74", text=[f"{v}" if v > 0 else "" for v in comp_log_lost], textposition="inside", insidetextanchor="middle", textfont=dict(color="#9a3412", weight="bold")))
        fig_bp_lost_spread.add_trace(go.Bar(name="Comp Sanction", y=shared_y_branches, x=comp_san_lost, orientation='h', marker_color="#f97316", text=[f"{v}" if v > 0 else "" for v in comp_san_lost], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))
        fig_bp_lost_spread.add_trace(go.Bar(name="Comp PF Paid", y=shared_y_branches, x=comp_pf_lost, orientation='h', marker_color="#9f1239", text=[f"{v}" if v > 0 else "" for v in comp_pf_lost], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))

        max_x = max(bp_lost_totals) if len(bp_lost_totals) > 0 else 100
        for i, branch in enumerate(shared_y_branches):
            if bp_lost_totals[i] > 0:
                fig_bp_lost_spread.add_annotation(x=bp_lost_totals[i], y=branch, text=f"<span style='color:#64748b; font-size:11px; font-weight:normal;'>Lost Potential</span><br><b style='font-size:16px; color:#9f1239;'>⚠️ {bp_potential_loss_pcts[i]}</b>", showarrow=False, xanchor="left", xshift=12, align="left")

        fig_bp_lost_spread.update_layout(barmode="stack", height=350, margin=dict(t=20, b=20, l=10, r=90), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False, range=[0, max_x + (max_x*0.3)]), yaxis=dict(showticklabels=False, autorange="reversed"), showlegend=False)
        st.plotly_chart(fig_bp_lost_spread, use_container_width=True)

    st.info("💡 **NOTE:** To connect Tabs 3 (Login-Sanction) and 4 (Sanction-PF) to this live data, copy the exact loop structures from Tab 2 above and update the column names (e.g. swap `date_shared` for `login_date` and filter for `lender_stage == 'Login'`).")
