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
# FIX: Using regex 'contains' makes this bulletproof against spaces, capitalization, or "Fall 2026" vs "Fall 26"
df_cohort = df[
    df['cohort'].astype(str).str.contains('fall', case=False, na=False) & 
    df['cohort'].astype(str).str.contains('26', case=False, na=False)
].copy()

# Initialize our Top-Level Navigational Tabs
tab_overall, tab_bp_login, tab_log_san, tab_san_pf = st.tabs([
    "🌐 Overall Performance", 
    "🔍 BP to Login",
    "📝 Login to Sanction",
    "✅ Sanction to PF"
])

# ==========================================
# TAB 1: OVERALL PERFORMANCE (DATE-DRIVEN & COHORT)
# ==========================================
with tab_overall:
    # --- SECTION 1: Y-O-Y COMPARISONS (SIDE-BY-SIDE) ---
    st.markdown('<div class="section-header"><h2>📈 1. Y-o-Y Performance & Monthly Logins</h2></div>', unsafe_allow_html=True)
    
    st.text_area(label="Notes", placeholder="Type your insights, talking points, or action items here...", label_visibility="collapsed", key="note_yoy_metrics")

    # --- TAB 1 YTD DATE LOGIC ---
    today = pd.to_datetime('today')
    f26_start = pd.to_datetime(f"{today.year}-01-01")
    f26_end = today
    f25_start = pd.to_datetime(f"{today.year - 1}-01-01")
    f25_end = today.replace(year=today.year - 1)

    def count_ytd(dataframe, date_col, start_dt, end_dt):
        return ((dataframe[date_col] >= start_dt) & (dataframe[date_col] <= end_dt)).sum()

    fall_26_data = [
        count_ytd(df, 'date_shared', f26_start, f26_end),
        count_ytd(df, 'login_date', f26_start, f26_end),
        count_ytd(df, 'sanction_date', f26_start, f26_end),
        count_ytd(df, 'pf_date', f26_start, f26_end)
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
            if yoy_growth[i] != "N/A":
                growth_annotations.append(dict(
                    x=stage, y=y_max + (y_max * 0.15) if y_max > 0 else 10, 
                    text=f"<b>{icon} {yoy_growth[i]}</b><br><span style='font-size:11px'>YoY Growth</span>",
                    showarrow=False, font=dict(size=14, color="black"), bgcolor="#f8fafc", bordercolor="#94a3b8", borderwidth=1, borderpad=6
                ))

        max_y_val = max(fall_26_data + fall_25_data) if (fall_26_data + fall_25_data) else 100
        fig_top_metrics.update_layout(barmode='group', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(gridcolor='#e2e8f0', range=[0, max_y_val * 1.35]), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5), annotations=growth_annotations, margin=dict(t=80))
        st.plotly_chart(fig_top_metrics, use_container_width=True)

    with col2:
        st.subheader("YoY Monthly Logins")
        df_logins_26 = df[(df['login_date'] >= f26_start) & (df['login_date'] <= f26_end)]
        df_logins_25 = df[(df['login_date'] >= f25_start) & (df['login_date'] <= f25_end)]
        
        f26_monthly = df_logins_26['login_date'].dt.month.value_counts().sort_index()
        f25_monthly = df_logins_25['login_date'].dt.month.value_counts().sort_index()
        
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        current_month = today.month
        months_list = month_names[:current_month]
        
        fall_26_logins = [f26_monthly.get(m, 0) for m in range(1, current_month + 1)]
        fall_25_logins = [f25_monthly.get(m, 0) for m in range(1, current_month + 1)]
        
        mom_growth = []
        for f26, f25 in zip(fall_26_logins, fall_25_logins):
            if f25 > 0:
                growth = ((f26 - f25) / f25) * 100
                mom_growth.append(f"+{growth:.1f}%" if growth >= 0 else f"{growth:.1f}%")
            else:
                mom_growth.append("N/A")
                
        fig_yoy_bar = go.Figure()
        fig_yoy_bar.add_trace(go.Bar(name="Fall '26", x=months_list, y=fall_26_logins, marker_color=COLOR_FALL_26, text=fall_26_logins, textposition='outside', textfont=dict(size=14, color='black')))
        fig_yoy_bar.add_trace(go.Bar(name="Fall '25", x=months_list, y=fall_25_logins, marker_color=COLOR_FALL_25, text=fall_25_logins, textposition='outside', textfont=dict(size=14, color='black')))

        mom_annotations = []
        for i, month in enumerate(months_list):
            y_max = max(fall_26_logins[i], fall_25_logins[i])
            icon = "⬇" if "-" in mom_growth[i] else "⬆"
            if mom_growth[i] != "N/A":
                mom_annotations.append(dict(x=month, y=y_max + (y_max * 0.15) if y_max > 0 else 10, text=f"<b>{icon} {mom_growth[i]}</b><br><span style='font-size:11px'>Growth</span>", showarrow=False, font=dict(size=13, color="black"), bgcolor="#f8fafc", bordercolor="#94a3b8", borderwidth=1, borderpad=6))

        max_y_log = max(fall_26_logins + fall_25_logins) if (fall_26_logins + fall_25_logins) else 100
        fig_yoy_bar.update_layout(barmode='group', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(gridcolor='#e2e8f0', range=[0, max_y_log * 1.35]), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5), annotations=mom_annotations, margin=dict(t=80))
        st.plotly_chart(fig_yoy_bar, use_container_width=True)
    
    st.divider()

    # --- SECTION 2: FALL 26 M-O-M PROGRESSION ---
    st.markdown('<div class="section-header"><h2>📅 2. Fall 26 M-o-M Progression by Stage</h2></div>', unsafe_allow_html=True)
    st.markdown("Tracking how the current Fall '26 pipeline is converting through all stages month-over-month.")
    
    def get_monthly_counts(date_series, max_month):
        counts = date_series.dt.month.value_counts().reindex(range(1, max_month + 1), fill_value=0)
        return counts.tolist()

    shared_mom = get_monthly_counts(df_cohort['date_shared'], current_month)
    login_mom = get_monthly_counts(df_cohort['login_date'], current_month)
    sanc_mom = get_monthly_counts(df_cohort['sanction_date'], current_month)
    pf_mom = get_monthly_counts(df_cohort['pf_date'], current_month)

    fig_mom = go.Figure()
    fig_mom.add_trace(go.Bar(name='Shared', x=months_list, y=shared_mom, marker_color='#a78bfa', text=shared_mom, textposition='outside'))
    fig_mom.add_trace(go.Bar(name='Login', x=months_list, y=login_mom, marker_color='#fda4af', text=login_mom, textposition='outside'))
    fig_mom.add_trace(go.Bar(name='Sanction', x=months_list, y=sanc_mom, marker_color='#fef08a', text=sanc_mom, textposition='outside'))
    fig_mom.add_trace(go.Bar(name='PF Paid', x=months_list, y=pf_mom, marker_color='#a7f3d0', text=pf_mom, textposition='outside'))

    fig_mom.update_traces(textfont=dict(size=12, color="black"))
    max_mom_val = max(shared_mom) if shared_mom else 100
    fig_mom.update_layout(barmode='group', height=380, margin=dict(t=40, b=20, l=20, r=20), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', yaxis=dict(gridcolor='#e2e8f0', range=[0, max_mom_val * 1.2]), legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5, title=None))
    st.plotly_chart(fig_mom, use_container_width=True)

    st.divider()

    # --- SECTION 3: SHARED LEAD COHORT FUNNEL ---
    st.markdown('<div class="section-header"><h2>🧬 3. Shared Leads Pipeline (Fall 26 Cohort)</h2></div>', unsafe_allow_html=True)
    st.markdown("Left-to-Right pipeline tracking active volumes, drop-offs, and true stage-to-stage conversion. <br><span style='color:#a7f3d0; font-size:18px'>●</span> <b>Current (Active)</b> &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#fca5a5; font-size:18px'>●</span> <b>Lost (Dropped)</b>", unsafe_allow_html=True)
    
    tot_shared = df_cohort['date_shared'].notnull().sum()
    tot_login = df_cohort['login_date'].notnull().sum()
    tot_sanc = df_cohort['sanction_date'].notnull().sum()
    tot_pf = df_cohort['pf_date'].notnull().sum()
    totals = [tot_shared, tot_login, tot_sanc, tot_pf]
    
    curr_bp = df_cohort[df_cohort['lender_stage'] == 'Bank Prospect'].shape[0]
    curr_log = df_cohort[df_cohort['lender_stage'] == 'Login'].shape[0]
    curr_san = df_cohort[df_cohort['lender_stage'] == 'Sanction'].shape[0]
    currents = [curr_bp, curr_log, curr_san, tot_pf] 

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

    bp_log_pct = (tot_login/tot_shared)*100 if tot_shared > 0 else 0
    log_san_pct = (tot_sanc/tot_login)*100 if tot_login > 0 else 0
    san_pf_pct = (tot_pf/tot_sanc)*100 if tot_sanc > 0 else 0
    
    fig_funnel.add_annotation(x=0.5, y=1.05, xref="x", yref="paper", text=f"<b>{bp_log_pct:.1f}% ➔</b>", showarrow=False, font=dict(size=14, color="#4f46e5"), bgcolor="#ffffff", bordercolor="#e2e8f0", borderwidth=1, borderpad=5)
    fig_funnel.add_annotation(x=1.5, y=1.05, xref="x", yref="paper", text=f"<b>{log_san_pct:.1f}% ➔</b>", showarrow=False, font=dict(size=14, color="#4f46e5"), bgcolor="#ffffff", bordercolor="#e2e8f0", borderwidth=1, borderpad=5)
    fig_funnel.add_annotation(x=2.5, y=1.05, xref="x", yref="paper", text=f"<b>{san_pf_pct:.1f}% ➔</b>", showarrow=False, font=dict(size=14, color="#4f46e5"), bgcolor="#ffffff", bordercolor="#e2e8f0", borderwidth=1, borderpad=5)
    
    max_funnel_range = max(totals) * 0.6 if totals else 1600
    fig_funnel.update_layout(height=400, margin={"t": 70, "b": 40, "l": 20, "r": 20}, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(showline=False, tickfont=dict(size=15, weight="bold", color="#1e293b")), yaxis=dict(showticklabels=False, showgrid=False, range=[-max_funnel_range, max_funnel_range]))
    st.plotly_chart(fig_funnel, use_container_width=True)

    st.divider()

    # --- SECTION 4: ACTIVE PIPELINE HEALTH ---
    st.markdown('<div class="section-header"><h2>⏱️ 4. Active Pipeline Health</h2></div>', unsafe_allow_html=True)
    st.markdown("A macro view of your active pipeline. Breaking down healthy leads vs. aging bottlenecks vs. competitor leakage.")

    active_bp = df_cohort[df_cohort['lender_stage'] == 'Bank Prospect'].copy()
    active_log = df_cohort[df_cohort['lender_stage'] == 'Login'].copy()
    active_san = df_cohort[df_cohort['lender_stage'] == 'Sanction'].copy()
    
    lost_bp_df = df_cohort[df_cohort['lost_category'] == 'Lost from BP']
    lost_log_df = df_cohort[df_cohort['lost_category'] == 'Lost from Login']
    lost_san_df = df_cohort[df_cohort['lost_category'] == 'Lost from Sanction']

    stages_health = [f"<b>BP Stage</b><br>{curr_bp} Leads", f"<b>Login Stage</b><br>{curr_log} Leads", f"<b>Sanction Stage</b><br>{curr_san} Leads"]

    under_7_vals = [
        (today - active_bp['date_shared']).dt.days.lt(7).sum(),
        (today - active_log['login_date']).dt.days.lt(7).sum(),
        (today - active_san['sanction_date']).dt.days.lt(7).sum()
    ]
    
    over_7_vals = [
        (today - active_bp['date_shared']).dt.days.ge(7).sum(),
        (today - active_log['login_date']).dt.days.ge(7).sum(),
        (today - active_san['sanction_date']).dt.days.ge(7).sum()
    ]
    
    # Lost to Comp (Lost from this stage, but reached higher overall)
    comp_vals = [
        lost_bp_df[lost_bp_df['user_max_stage'] > 1].shape[0],
        lost_log_df[lost_log_df['user_max_stage'] > 2].shape[0],
        lost_san_df[lost_san_df['user_max_stage'] > 3].shape[0]
    ]

    totals_health = [u + o + c for u, o, c in zip(under_7_vals, over_7_vals, comp_vals)]
    under_7_pcts = [f"{(v/t)*100:.0f}%" if t > 0 else "0%" for v, t in zip(under_7_vals, totals_health)]
    over_7_pcts  = [f"{(v/t)*100:.0f}%" if t > 0 else "0%" for v, t in zip(over_7_vals, totals_health)]
    comp_pcts    = [f"{(v/t)*100:.0f}%" if t > 0 else "0%" for v, t in zip(comp_vals, totals_health)]

    fig_health_bar = go.Figure()
    fig_health_bar.add_trace(go.Bar(name="< 7 Days (Active)", y=stages_health, x=under_7_vals, orientation='h', marker_color="#a7f3d0", text=[f"{v} ({p})" if v > 0 else "" for v, p in zip(under_7_vals, under_7_pcts)], textposition="inside", insidetextanchor="middle", insidetextfont=dict(color="#0f172a", size=14, weight="bold")))
    fig_health_bar.add_trace(go.Bar(name="> 7 Days (Aging)", y=stages_health, x=over_7_vals, orientation='h', marker_color="#fed7aa", text=[f"{v} ({p})" if v > 0 else "" for v, p in zip(over_7_vals, over_7_pcts)], textposition="inside", insidetextanchor="middle", insidetextfont=dict(color="#0f172a", size=14, weight="bold")))
    fig_health_bar.add_trace(go.Bar(name="Lost to Competitor", y=stages_health, x=comp_vals, orientation='h', marker_color="#9f1239", text=[f"{v} ({p})" if v > 0 else "" for v, p in zip(comp_vals, comp_pcts)], textposition="inside", insidetextanchor="middle", insidetextfont=dict(color="white", size=14, weight="bold")))

    fig_health_bar.update_layout(barmode="stack", height=320, margin=dict(t=40, b=20, l=20, r=20), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showgrid=False, tickfont=dict(size=15, color="#1e293b"), autorange="reversed"))
    st.plotly_chart(fig_health_bar, use_container_width=True)

    st.divider()

    # --- SECTION 5: LOSING THE ACTIVE PROSPECTS ---
    st.markdown('<div class="section-header"><h2>💸 5. Losing The Active Prospects</h2></div>', unsafe_allow_html=True)
    st.markdown("Where our workable leads are currently sitting (Exclusive vs. Flight Risk).")

    stages_loss = [f"<b>Login Stage</b><br>{curr_log} Active Leads", f"<b>BP Stage</b><br>{curr_bp} Active Leads"]

    exc_vals = [
        active_log[active_log['user_max_stage'] <= 2].shape[0],
        active_bp[active_bp['user_max_stage'] == 1].shape[0]
    ]
    clog_vals = [
        0, # active login leads are already in login
        active_bp[active_bp['user_max_stage'] == 2].shape[0]
    ]
    csan_vals = [
        active_log[active_log['user_max_stage'] == 3].shape[0],
        active_bp[active_bp['user_max_stage'] == 3].shape[0]
    ]
    
    totals_loss = [e + l + s for e, l, s in zip(exc_vals, clog_vals, csan_vals)]
    exc_pcts = [f"{(v/t)*100:.0f}%" if t > 0 else "0%" for v, t in zip(exc_vals, totals_loss)]
    clog_pcts = [f"{(v/t)*100:.0f}%" if t > 0 else "0%" for v, t in zip(clog_vals, totals_loss)]
    csan_pcts = [f"{(v/t)*100:.0f}%" if t > 0 else "0%" for v, t in zip(csan_vals, totals_loss)]

    fig_loss_bar = go.Figure()
    fig_loss_bar.add_trace(go.Bar(name="✅ Exclusive (Safe)", y=stages_loss, x=exc_vals, orientation='h', marker_color="#a7f3d0", text=[f"{v} ({p})" if v > 0 else "" for v, p in zip(exc_vals, exc_pcts)], textposition="inside", insidetextanchor="middle", insidetextfont=dict(color="#0f172a", size=14, weight="bold")))
    fig_loss_bar.add_trace(go.Bar(name="⚠️ In Competitor Login", y=stages_loss, x=clog_vals, orientation='h', marker_color="#fed7aa", text=[f"{v} ({p})" if v > 0 else "" for v, p in zip(clog_vals, clog_pcts)], textposition="inside", insidetextanchor="middle", insidetextfont=dict(color="#0f172a", size=14, weight="bold")))
    fig_loss_bar.add_trace(go.Bar(name="🚨 In Competitor Sanction", y=stages_loss, x=csan_vals, orientation='h', marker_color="#9f1239", text=[f"{v} ({p})" if v > 0 else "" for v, p in zip(csan_vals, csan_pcts)], textposition="inside", insidetextanchor="middle", insidetextfont=dict(color="white", size=14, weight="bold")))

    fig_loss_bar.update_layout(barmode="stack", height=280, margin=dict(t=40, b=20, l=20, r=20), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showgrid=False, tickfont=dict(size=15, color="#1e293b")))
    st.plotly_chart(fig_loss_bar, use_container_width=True)

    st.divider()

    # --- SECTION 6: LOST POTENTIAL ANALYSIS ---
    st.markdown('<div class="section-header"><h2>🚨 6. Lost Potential Analysis</h2></div>', unsafe_allow_html=True)
    st.subheader("Flight Risk: Where are they in the Competitor's Funnel?")
    st.markdown("Out of the total files lost at each stage, this tracks how many went to a competitor and **exactly what stage the competitor has reached with them**.")

    stages_lost = [f"<b>Lost from Sanction</b><br>({lost_san} Total)", f"<b>Lost from Login</b><br>({lost_log} Total)", f"<b>Lost from BP</b><br>({lost_bp} Total)"]
    bar_totals = [lost_san, lost_log, lost_bp]

    true_dead = [
        lost_san_df[lost_san_df['user_max_stage'] <= 3].shape[0],
        lost_log_df[lost_log_df['user_max_stage'] <= 2].shape[0],
        lost_bp_df[lost_bp_df['user_max_stage'] == 1].shape[0]
    ]
    comp_login = [
        0, 0, lost_bp_df[lost_bp_df['user_max_stage'] == 2].shape[0]
    ]
    comp_sanc = [
        0, 
        lost_log_df[lost_log_df['user_max_stage'] == 3].shape[0],
        lost_bp_df[lost_bp_df['user_max_stage'] == 3].shape[0]
    ]
    comp_pf = [
        lost_san_df[lost_san_df['user_max_stage'] == 4].shape[0],
        lost_log_df[lost_log_df['user_max_stage'] == 4].shape[0],
        lost_bp_df[lost_bp_df['user_max_stage'] == 4].shape[0]
    ]

    potential_loss_pcts = [f"{((t - td) / t) * 100:.1f}%" if t > 0 else "0%" for t, td in zip(bar_totals, true_dead)]

    fig_flight = go.Figure()
    fig_flight.add_trace(go.Bar(name="True Dead (No Competitor Action)", y=stages_lost, x=true_dead, orientation='h', marker_color="#e2e8f0", text=[f"{v}" if v > 0 else "" for v in true_dead], textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")))
    fig_flight.add_trace(go.Bar(name="In Competitor Login", y=stages_lost, x=comp_login, orientation='h', marker_color="#fdba74", text=[f"{v}" if v > 0 else "" for v in comp_login], textposition="inside", insidetextanchor="middle", textfont=dict(color="#9a3412", weight="bold")))
    fig_flight.add_trace(go.Bar(name="In Competitor Sanction", y=stages_lost, x=comp_sanc, orientation='h', marker_color="#f97316", text=[f"{v}" if v > 0 else "" for v in comp_sanc], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))
    fig_flight.add_trace(go.Bar(name="Competitor PF Paid (Fully Lost)", y=stages_lost, x=comp_pf, orientation='h', marker_color="#9f1239", text=[f"{v}" if v > 0 else "" for v in comp_pf], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))

    max_bar_tot = max(bar_totals) if bar_totals else 100
    for i, stage in enumerate(stages_lost):
        if bar_totals[i] > 0:
            fig_flight.add_annotation(x=bar_totals[i], y=stage, text=f"<span style='color:#64748b; font-size:11px; font-weight:normal;'>Potential Loss</span><br><b style='font-size:16px; color:#9f1239;'>⚠️ {potential_loss_pcts[i]}</b>", showarrow=False, xanchor="left", xshift=15, align="left")

    fig_flight.update_layout(barmode="stack", height=320, margin=dict(t=40, b=20, l=20, r=100), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False, range=[0, max_bar_tot * 1.3]), yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b")))
    st.plotly_chart(fig_flight, use_container_width=True)

    st.divider()

    # --- PART B: REASONS FOR LOSS ---
    st.subheader("Reason for Loss Matrix")
    col_r1, col_r2, col_r3 = st.columns(3)

    def get_top_reasons(df_lost, color):
        if df_lost.empty:
            return go.Figure()
        reasons = df_lost['lost_reason'].value_counts().head(5).sort_values(ascending=True)
        fig = go.Figure(go.Bar(y=reasons.index, x=reasons.values, orientation='h', marker_color=color, text=reasons.values, textposition='outside', textfont=dict(weight="bold", color="#1e293b")))
        fig.update_layout(height=280, margin=dict(t=20, b=20, l=10, r=40), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showgrid=False, tickfont=dict(weight="bold", color="#475569")))
        return fig

    with col_r1:
        st.markdown("**1. Lost from BP Stage**")
        st.plotly_chart(get_top_reasons(lost_bp_df, '#94a3b8'), use_container_width=True)

    with col_r2:
        st.markdown("**2. Lost from Login Stage**")
        st.plotly_chart(get_top_reasons(lost_log_df, '#64748b'), use_container_width=True)

    with col_r3:
        st.markdown("**3. Lost from Sanction Stage**")
        st.plotly_chart(get_top_reasons(lost_san_df, '#475569'), use_container_width=True)

# ==========================================
# TAB 2: BP TO LOGIN DEEP DIVE (COHORT-DRIVEN)
# ==========================================
with tab_bp_login:
    # --- DYNAMIC DATA PREP FOR BP ---
    bp_df = df_cohort[df_cohort['date_shared'].notnull()]
    
    branch_counts = bp_df['location'].value_counts()
    top_branches = branch_counts.head(5).index.tolist()
    
    if len(branch_counts) > 5:
        top_branches.append("Others")
        bp_vols = branch_counts.head(5).tolist() + [branch_counts.iloc[5:].sum()]
    else:
        bp_vols = branch_counts.tolist()
        
    total_bp_pie = sum(bp_vols) if sum(bp_vols) > 0 else 1
    bp_pcts = [f"{(v/total_bp_pie)*100:.1f}%" for v in bp_vols]
    shared_y_branches = [b for b in top_branches if b != "Others"]

    st.markdown('<div class="section-header"><h2>🗂️ BP Stage Lead Distribution</h2></div>', unsafe_allow_html=True)
    card_cols = st.columns(6)
    for i, col in enumerate(card_cols):
        if i < len(top_branches):
            with col:
                st.metric(label=f"📍 {top_branches[i]}", value=f"{bp_vols[i]:,} Leads", delta=f"{bp_pcts[i]} Share", delta_color="off")
    st.divider()

    # --- AGGREGATION ENGINE ---
    conv_rates, tat_days, true_active_bp, paid_comp_bp = [], [], [], []
    bp_under_7, bp_over_7 = [], []
    bp_exclusive, bp_comp_login, bp_comp_sanc = [], [], []

    active_bp_df = bp_df[bp_df['lender_stage'] == 'Bank Prospect'].copy()
    active_bp_df['aging_days'] = (pd.to_datetime('today') - active_bp_df['date_shared']).dt.days

    for b in shared_y_branches:
        b_df = bp_df[bp_df['location'] == b]
        shared_c = b_df.shape[0]
        log_c = b_df['login_date'].notnull().sum()
        
        conv_rates.append(round((log_c/shared_c)*100, 1) if shared_c > 0 else 0)
        tat_days.append(round(b_df['tat_bp_login'].mean(), 1) if not pd.isna(b_df['tat_bp_login'].mean()) else 0)
        
        b_act = active_bp_df[active_bp_df['location'] == b]
        true_active_bp.append(b_act[b_act['user_max_stage'] < 4].shape[0]) 
        paid_comp_bp.append(b_act[b_act['user_max_stage'] == 4].shape[0])  
        
        bp_under_7.append(b_act[b_act['aging_days'] < 7].shape[0])
        bp_over_7.append(b_act[b_act['aging_days'] >= 7].shape[0])
        
        bp_exclusive.append(b_act[b_act['user_max_stage'] == 1].shape[0])
        bp_comp_login.append(b_act[b_act['user_max_stage'] == 2].shape[0])
        bp_comp_sanc.append(b_act[b_act['user_max_stage'] == 3].shape[0])

    st.markdown('<div class="section-header"><h2>📊 1. Conversion, Aging & Immediate Flight Risk</h2></div>', unsafe_allow_html=True)
    col_c1, col_c2, col_c3 = st.columns(3)
    
    with col_c1:
        nat_avg = round((df_cohort['login_date'].notnull().sum() / df_cohort['date_shared'].notnull().sum())*100, 1) if df_cohort['date_shared'].notnull().sum() > 0 else 0
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
    lost_bp_df = bp_df[bp_df['lost_category'] == 'Lost from BP']
    true_dead_lost, comp_log_lost, comp_san_lost, comp_pf_lost, bp_leakage_pcts = [], [], [], [], []
    
    for b in shared_y_branches:
        total_shared_b = bp_df[bp_df['location'] == b].shape[0]
        b_lost = lost_bp_df[lost_bp_df['location'] == b]
        total_lost_b = b_lost.shape[0]
        
        bp_leakage_pcts.append(round((total_lost_b / total_shared_b)*100, 1) if total_shared_b > 0 else 0)
        
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

# ==========================================
# TAB 3: LOGIN TO SANCTION DEEP DIVE
# ==========================================
with tab_log_san:
    log_df = df_cohort[df_cohort['login_date'].notnull()]
    
    branch_counts = log_df['location'].value_counts()
    top_branches = branch_counts.head(5).index.tolist()
    if len(branch_counts) > 5:
        top_branches.append("Others")
        log_vols = branch_counts.head(5).tolist() + [branch_counts.iloc[5:].sum()]
    else:
        log_vols = branch_counts.tolist()
        
    total_log_pie = sum(log_vols) if sum(log_vols) > 0 else 1
    log_pcts = [f"{(v/total_log_pie)*100:.1f}%" for v in log_vols]
    shared_y_branches = [b for b in top_branches if b != "Others"]

    st.markdown('<div class="section-header"><h2>🗂️ Login Stage Lead Distribution</h2></div>', unsafe_allow_html=True)
    card_cols = st.columns(6)
    for i, col in enumerate(card_cols):
        if i < len(top_branches):
            with col:
                st.metric(label=f"📍 {top_branches[i]}", value=f"{log_vols[i]:,} Logins", delta=f"{log_pcts[i]} Share", delta_color="off")
    st.divider()

    # --- AGGREGATION ENGINE ---
    conv_rates, tat_days, true_active_log, paid_comp_log = [], [], [], []
    log_under_7, log_over_7 = [], []
    log_exclusive, log_comp_sanc = [], []

    active_log_df = log_df[log_df['lender_stage'] == 'Login'].copy()
    active_log_df['aging_days'] = (pd.to_datetime('today') - active_log_df['login_date']).dt.days

    for b in shared_y_branches:
        b_df = log_df[log_df['location'] == b]
        log_c = b_df.shape[0]
        san_c = b_df['sanction_date'].notnull().sum()
        
        conv_rates.append(round((san_c/log_c)*100, 1) if log_c > 0 else 0)
        tat_days.append(round(b_df['tat_login_sanc'].mean(), 1) if not pd.isna(b_df['tat_login_sanc'].mean()) else 0)
        
        b_act = active_log_df[active_log_df['location'] == b]
        true_active_log.append(b_act[b_act['user_max_stage'] < 4].shape[0]) 
        paid_comp_log.append(b_act[b_act['user_max_stage'] == 4].shape[0])  
        
        log_under_7.append(b_act[b_act['aging_days'] < 7].shape[0])
        log_over_7.append(b_act[b_act['aging_days'] >= 7].shape[0])
        
        log_exclusive.append(b_act[b_act['user_max_stage'] <= 2].shape[0])
        log_comp_sanc.append(b_act[b_act['user_max_stage'] == 3].shape[0])

    st.markdown('<div class="section-header"><h2>📊 1. Conversion, Aging & Immediate Flight Risk</h2></div>', unsafe_allow_html=True)
    col_c1, col_c2, col_c3 = st.columns(3)
    
    with col_c1:
        nat_avg = round((df_cohort['sanction_date'].notnull().sum() / df_cohort['login_date'].notnull().sum())*100, 1) if df_cohort['login_date'].notnull().sum() > 0 else 0
        st.markdown(f"<h4 style='text-align: center; color: #475569;'>Login ➔ Sanction Rate<br><span style='font-size:14px; font-weight:normal;'>(Nat. Avg: {nat_avg}%)</span></h4>", unsafe_allow_html=True)
        conv_colors = ["#9f1239" if val < nat_avg else "#cbd5e1" for val in conv_rates]
        fig_conv = go.Figure(go.Bar(y=shared_y_branches, x=conv_rates, orientation='h', marker_color=conv_colors, text=[f"{v}%" for v in conv_rates], textposition="inside", insidetextanchor="middle", textfont=dict(color=["white" if c == "#9f1239" else "#0f172a" for c in conv_colors], weight="bold")))
        fig_conv.add_vline(x=nat_avg, line_dash="dash", line_color="#475569", line_width=2)
        fig_conv.update_layout(height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569")))
        st.plotly_chart(fig_conv, use_container_width=True)

    with col_c2:
        target_tat = 3.0
        st.markdown(f"<h4 style='text-align: center; color: #475569;'>Login ➔ Sanction TAT<br><span style='font-size:14px; font-weight:normal;'>(Target SLA: {target_tat} Days)</span></h4>", unsafe_allow_html=True)
        tat_colors = ["#9f1239" if val > target_tat else "#cbd5e1" for val in tat_days]
        fig_tat = go.Figure(go.Bar(y=shared_y_branches, x=tat_days, orientation='h', marker_color=tat_colors, text=[f"{v} days" for v in tat_days], textposition="inside", insidetextanchor="middle", textfont=dict(color=["white" if c == "#9f1239" else "#0f172a" for c in tat_colors], weight="bold")))
        fig_tat.add_vline(x=target_tat, line_dash="dash", line_color="#475569", line_width=2)
        fig_tat.update_layout(height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
        st.plotly_chart(fig_tat, use_container_width=True)

    with col_c3:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Active Login vs. Paid to Competitor<br><span style='font-size:14px; font-weight:normal;'><span style='color:#cbd5e1'>■</span> True Active Login &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#f97316'>■</span> Paid Competitor</span></h4>", unsafe_allow_html=True)
        paid_pcts = [f"({int((p/(a+p))*100)}%)" if (a+p)>0 else "(0%)" for a, p in zip(true_active_log, paid_comp_log)]
        fig_flight = go.Figure()
        fig_flight.add_trace(go.Bar(name="True Active Login", y=shared_y_branches, x=true_active_log, orientation='h', marker_color="#e2e8f0", text=[v if v>0 else "" for v in true_active_log], textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")))
        fig_flight.add_trace(go.Bar(name="Paid Competitor", y=shared_y_branches, x=paid_comp_log, orientation='h', marker_color="#f97316", text=[f"{v} {pct}" if v>0 else "" for v, pct in zip(paid_comp_log, paid_pcts)], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))
        fig_flight.update_layout(barmode="stack", height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"), showlegend=False)
        st.plotly_chart(fig_flight, use_container_width=True)

    st.divider()

    st.subheader("🔎 True Workable Login Leads Breakdown")
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Active Leads Aging</h4>", unsafe_allow_html=True)
        fig_log_aging = go.Figure()
        fig_log_aging.add_trace(go.Bar(name="< 7 Days", y=shared_y_branches, x=log_under_7, orientation='h', marker_color="#60a5fa", text=[f"{v}" if v > 0 else "" for v in log_under_7], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))
        fig_log_aging.add_trace(go.Bar(name="> 7 Days", y=shared_y_branches, x=log_over_7, orientation='h', marker_color="#ef4444", text=[f"{v}" if v > 0 else "" for v in log_over_7], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))
        fig_log_aging.update_layout(barmode="stack", height=380, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569")))
        st.plotly_chart(fig_log_aging, use_container_width=True)

    with col_w2:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Competitor Pipeline Spread</h4>", unsafe_allow_html=True)
        fig_log_work = go.Figure()
        fig_log_work.add_trace(go.Bar(name="Exclusive (Safe)", y=shared_y_branches, x=log_exclusive, orientation='h', marker_color="#a7f3d0", text=[f"{v}" if v > 0 else "" for v in log_exclusive], textposition="inside", insidetextanchor="middle", textfont=dict(color="#0f172a", weight="bold")))
        fig_log_work.add_trace(go.Bar(name="🚨 In Comp Sanction", y=shared_y_branches, x=log_comp_sanc, orientation='h', marker_color="#fda4af", text=[f"{v}" if v > 0 else "" for v in log_comp_sanc], textposition="inside", insidetextanchor="middle", textfont=dict(color="#881337", weight="bold")))
        fig_log_work.update_layout(barmode="stack", height=380, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
        st.plotly_chart(fig_log_work, use_container_width=True)
    
    st.divider()

    # --- SECTION 3: LOGIN STAGE LOST ANALYSIS ---
    lost_log_df = log_df[log_df['lost_category'] == 'Lost from Login']
    true_dead_lost, comp_san_lost, comp_pf_lost, log_leakage_pcts = [], [], [], []
    
    for b in shared_y_branches:
        total_shared_b = log_df[log_df['location'] == b].shape[0]
        b_lost = lost_log_df[lost_log_df['location'] == b]
        total_lost_b = b_lost.shape[0]
        
        log_leakage_pcts.append(round((total_lost_b / total_shared_b)*100, 1) if total_shared_b > 0 else 0)
        
        true_dead_lost.append(b_lost[b_lost['user_max_stage'] <= 2].shape[0])
        comp_san_lost.append(b_lost[b_lost['user_max_stage'] == 3].shape[0])
        comp_pf_lost.append(b_lost[b_lost['user_max_stage'] == 4].shape[0])

    st.markdown('<div class="section-header"><h2>🚨 3. Login Stage Lost Analysis</h2></div>', unsafe_allow_html=True)
    col_l1, col_l2 = st.columns(2)

    with col_l1:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Login Leakage Rate (% of Logins)<br><span style='font-size:13px; visibility:hidden;'>Invisible Spacer</span></h4>", unsafe_allow_html=True)
        leakage_colors = ["#9f1239" if p > 30 else ("#ef4444" if p > 20 else "#fca5a5") for p in log_leakage_pcts]
        fig_log_leakage = go.Figure(go.Bar(y=shared_y_branches, x=log_leakage_pcts, orientation='h', marker_color=leakage_colors, text=[f"{p}%" for p in log_leakage_pcts], textposition="inside", insidetextanchor="middle", textfont=dict(color=["white" if c in ["#9f1239", "#ef4444"] else "#0f172a" for c in leakage_colors], weight="bold")))
        fig_log_leakage.update_layout(height=350, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569")))
        st.plotly_chart(fig_log_leakage, use_container_width=True)

    with col_l2:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Competitor Pipeline Spread (Lost Leads)<br><span style='font-size:13px; font-weight:normal;'><span style='color:#e2e8f0'>■</span> True Dead &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#f97316'>■</span> Comp Sanction &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#9f1239'>■</span> Comp PF Paid</span></h4>", unsafe_allow_html=True)
        log_lost_totals = [t + s + p for t, s, p in zip(true_dead_lost, comp_san_lost, comp_pf_lost)]
        log_potential_loss_pcts = [f"{((tot - td) / tot) * 100:.1f}%" if tot > 0 else "0%" for tot, td in zip(log_lost_totals, true_dead_lost)]

        fig_log_lost_spread = go.Figure()
        fig_log_lost_spread.add_trace(go.Bar(name="True Dead", y=shared_y_branches, x=true_dead_lost, orientation='h', marker_color="#e2e8f0", text=[f"{v}" if v > 0 else "" for v in true_dead_lost], textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")))
        fig_log_lost_spread.add_trace(go.Bar(name="Comp Sanction", y=shared_y_branches, x=comp_san_lost, orientation='h', marker_color="#f97316", text=[f"{v}" if v > 0 else "" for v in comp_san_lost], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))
        fig_log_lost_spread.add_trace(go.Bar(name="Comp PF Paid", y=shared_y_branches, x=comp_pf_lost, orientation='h', marker_color="#9f1239", text=[f"{v}" if v > 0 else "" for v in comp_pf_lost], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))

        max_x = max(log_lost_totals) if len(log_lost_totals) > 0 else 100
        for i, branch in enumerate(shared_y_branches):
            if log_lost_totals[i] > 0:
                fig_log_lost_spread.add_annotation(x=log_lost_totals[i], y=branch, text=f"<span style='color:#64748b; font-size:11px; font-weight:normal;'>Lost Potential</span><br><b style='font-size:16px; color:#9f1239;'>⚠️ {log_potential_loss_pcts[i]}</b>", showarrow=False, xanchor="left", xshift=12, align="left")

        fig_log_lost_spread.update_layout(barmode="stack", height=350, margin=dict(t=20, b=20, l=10, r=90), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False, range=[0, max_x + (max_x*0.3)]), yaxis=dict(showticklabels=False, autorange="reversed"), showlegend=False)
        st.plotly_chart(fig_log_lost_spread, use_container_width=True)

# ==========================================
# TAB 4: SANCTION TO PF DEEP DIVE
# ==========================================
with tab_san_pf:
    san_df = df_cohort[df_cohort['sanction_date'].notnull()]
    
    branch_counts = san_df['location'].value_counts()
    top_branches = branch_counts.head(5).index.tolist()
    if len(branch_counts) > 5:
        top_branches.append("Others")
        san_vols = branch_counts.head(5).tolist() + [branch_counts.iloc[5:].sum()]
    else:
        san_vols = branch_counts.tolist()
        
    total_san_pie = sum(san_vols) if sum(san_vols) > 0 else 1
    san_pcts = [f"{(v/total_san_pie)*100:.1f}%" for v in san_vols]
    shared_y_branches = [b for b in top_branches if b != "Others"]

    st.markdown('<div class="section-header"><h2>🗂️ Sanction Stage Lead Distribution</h2></div>', unsafe_allow_html=True)
    card_cols = st.columns(6)
    for i, col in enumerate(card_cols):
        if i < len(top_branches):
            with col:
                st.metric(label=f"📍 {top_branches[i]}", value=f"{san_vols[i]:,} Sanctions", delta=f"{san_pcts[i]} Share", delta_color="off")
    st.divider()

    # --- AGGREGATION ENGINE ---
    conv_rates, tat_days, true_active_san, paid_comp_san = [], [], [], []
    san_under_7, san_over_7 = [], []
    san_exclusive, san_comp_parallel = [], []

    active_san_df = san_df[san_df['lender_stage'] == 'Sanction'].copy()
    active_san_df['aging_days'] = (pd.to_datetime('today') - active_san_df['sanction_date']).dt.days

    for b in shared_y_branches:
        b_df = san_df[san_df['location'] == b]
        san_c = b_df.shape[0]
        pf_c = b_df['pf_date'].notnull().sum()
        
        conv_rates.append(round((pf_c/san_c)*100, 1) if san_c > 0 else 0)
        tat_days.append(round(b_df['tat_sanc_pf'].mean(), 1) if not pd.isna(b_df['tat_sanc_pf'].mean()) else 0)
        
        b_act = active_san_df[active_san_df['location'] == b]
        true_active_san.append(b_act[b_act['user_max_stage'] < 4].shape[0]) 
        paid_comp_san.append(b_act[b_act['user_max_stage'] == 4].shape[0])  
        
        san_under_7.append(b_act[b_act['aging_days'] < 7].shape[0])
        san_over_7.append(b_act[b_act['aging_days'] >= 7].shape[0])
        
        san_exclusive.append(b_act[b_act['user_max_stage'] <= 3].shape[0])
        san_comp_parallel.append(0) # In Sanction, flight risk is captured purely by PF paid above

    st.markdown('<div class="section-header"><h2>📊 1. Conversion, Aging & Immediate Flight Risk</h2></div>', unsafe_allow_html=True)
    col_c1, col_c2, col_c3 = st.columns(3)
    
    with col_c1:
        nat_avg = round((df_cohort['pf_date'].notnull().sum() / df_cohort['sanction_date'].notnull().sum())*100, 1) if df_cohort['sanction_date'].notnull().sum() > 0 else 0
        st.markdown(f"<h4 style='text-align: center; color: #475569;'>Sanction ➔ PF Rate<br><span style='font-size:14px; font-weight:normal;'>(Nat. Avg: {nat_avg}%)</span></h4>", unsafe_allow_html=True)
        conv_colors = ["#9f1239" if val < nat_avg else "#cbd5e1" for val in conv_rates]
        fig_conv = go.Figure(go.Bar(y=shared_y_branches, x=conv_rates, orientation='h', marker_color=conv_colors, text=[f"{v}%" for v in conv_rates], textposition="inside", insidetextanchor="middle", textfont=dict(color=["white" if c == "#9f1239" else "#0f172a" for c in conv_colors], weight="bold")))
        fig_conv.add_vline(x=nat_avg, line_dash="dash", line_color="#475569", line_width=2)
        fig_conv.update_layout(height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569")))
        st.plotly_chart(fig_conv, use_container_width=True)

    with col_c2:
        target_tat = 5.0
        st.markdown(f"<h4 style='text-align: center; color: #475569;'>Sanction ➔ PF TAT<br><span style='font-size:14px; font-weight:normal;'>(Target SLA: {target_tat} Days)</span></h4>", unsafe_allow_html=True)
        tat_colors = ["#9f1239" if val > target_tat else "#cbd5e1" for val in tat_days]
        fig_tat = go.Figure(go.Bar(y=shared_y_branches, x=tat_days, orientation='h', marker_color=tat_colors, text=[f"{v} days" for v in tat_days], textposition="inside", insidetextanchor="middle", textfont=dict(color=["white" if c == "#9f1239" else "#0f172a" for c in tat_colors], weight="bold")))
        fig_tat.add_vline(x=target_tat, line_dash="dash", line_color="#475569", line_width=2)
        fig_tat.update_layout(height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
        st.plotly_chart(fig_tat, use_container_width=True)

    with col_c3:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Active Sanction vs. Paid to Competitor<br><span style='font-size:14px; font-weight:normal;'><span style='color:#cbd5e1'>■</span> True Active Sanction &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#f97316'>■</span> Paid Competitor</span></h4>", unsafe_allow_html=True)
        paid_pcts = [f"({int((p/(a+p))*100)}%)" if (a+p)>0 else "(0%)" for a, p in zip(true_active_san, paid_comp_san)]
        fig_flight = go.Figure()
        fig_flight.add_trace(go.Bar(name="True Active Sanction", y=shared_y_branches, x=true_active_san, orientation='h', marker_color="#e2e8f0", text=[v if v>0 else "" for v in true_active_san], textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")))
        fig_flight.add_trace(go.Bar(name="Paid Competitor", y=shared_y_branches, x=paid_comp_san, orientation='h', marker_color="#f97316", text=[f"{v} {pct}" if v>0 else "" for v, pct in zip(paid_comp_san, paid_pcts)], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))
        fig_flight.update_layout(barmode="stack", height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"), showlegend=False)
        st.plotly_chart(fig_flight, use_container_width=True)

    st.divider()

    st.subheader("🔎 True Workable Sanction Leads Breakdown")
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Active Leads Aging</h4>", unsafe_allow_html=True)
        fig_san_aging = go.Figure()
        fig_san_aging.add_trace(go.Bar(name="< 7 Days", y=shared_y_branches, x=san_under_7, orientation='h', marker_color="#60a5fa", text=[f"{v}" if v > 0 else "" for v in san_under_7], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))
        fig_san_aging.add_trace(go.Bar(name="> 7 Days", y=shared_y_branches, x=san_over_7, orientation='h', marker_color="#ef4444", text=[f"{v}" if v > 0 else "" for v in san_over_7], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))
        fig_san_aging.update_layout(barmode="stack", height=380, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569")))
        st.plotly_chart(fig_san_aging, use_container_width=True)

    with col_w2:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Competitor Pipeline Spread</h4>", unsafe_allow_html=True)
        fig_san_work = go.Figure()
        fig_san_work.add_trace(go.Bar(name="Exclusive (Safe)", y=shared_y_branches, x=san_exclusive, orientation='h', marker_color="#a7f3d0", text=[f"{v}" if v > 0 else "" for v in san_exclusive], textposition="inside", insidetextanchor="middle", textfont=dict(color="#0f172a", weight="bold")))
        fig_san_work.add_trace(go.Bar(name="🚨 Parallel Comp Sanction", y=shared_y_branches, x=san_comp_parallel, orientation='h', marker_color="#fda4af", text=[f"{v}" if v > 0 else "" for v in san_comp_parallel], textposition="inside", insidetextanchor="middle", textfont=dict(color="#881337", weight="bold")))
        fig_san_work.update_layout(barmode="stack", height=380, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
        st.plotly_chart(fig_san_work, use_container_width=True)
    
    st.divider()

    # --- SECTION 3: SANCTION STAGE LOST ANALYSIS ---
    lost_san_df = san_df[san_df['lost_category'] == 'Lost from Sanction']
    true_dead_lost, comp_pf_lost, san_leakage_pcts = [], [], []
    
    for b in shared_y_branches:
        total_shared_b = san_df[san_df['location'] == b].shape[0]
        b_lost = lost_san_df[lost_san_df['location'] == b]
        total_lost_b = b_lost.shape[0]
        
        san_leakage_pcts.append(round((total_lost_b / total_shared_b)*100, 1) if total_shared_b > 0 else 0)
        true_dead_lost.append(b_lost[b_lost['user_max_stage'] <= 3].shape[0])
        comp_pf_lost.append(b_lost[b_lost['user_max_stage'] == 4].shape[0])

    st.markdown('<div class="section-header"><h2>🚨 3. Sanction Stage Lost Analysis</h2></div>', unsafe_allow_html=True)
    col_l1, col_l2 = st.columns(2)

    with col_l1:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Sanction Leakage Rate (% of Sanctions)<br><span style='font-size:13px; visibility:hidden;'>Invisible Spacer</span></h4>", unsafe_allow_html=True)
        leakage_colors = ["#9f1239" if p > 15 else ("#ef4444" if p > 5 else "#fca5a5") for p in san_leakage_pcts]
        fig_san_leakage = go.Figure(go.Bar(y=shared_y_branches, x=san_leakage_pcts, orientation='h', marker_color=leakage_colors, text=[f"{p}%" for p in san_leakage_pcts], textposition="inside", insidetextanchor="middle", textfont=dict(color=["white" if c in ["#9f1239", "#ef4444"] else "#0f172a" for c in leakage_colors], weight="bold")))
        fig_san_leakage.update_layout(height=350, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569")))
        st.plotly_chart(fig_san_leakage, use_container_width=True)

    with col_l2:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Competitor Pipeline Spread (Lost Leads)<br><span style='font-size:13px; font-weight:normal;'><span style='color:#e2e8f0'>■</span> True Dead &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#9f1239'>■</span> Comp PF Paid</span></h4>", unsafe_allow_html=True)
        san_lost_totals = [t + p for t, p in zip(true_dead_lost, comp_pf_lost)]
        san_potential_loss_pcts = [f"{((tot - td) / tot) * 100:.1f}%" if tot > 0 else "0%" for tot, td in zip(san_lost_totals, true_dead_lost)]

        fig_san_lost_spread = go.Figure()
        fig_san_lost_spread.add_trace(go.Bar(name="True Dead", y=shared_y_branches, x=true_dead_lost, orientation='h', marker_color="#e2e8f0", text=[f"{v}" if v > 0 else "" for v in true_dead_lost], textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")))
        fig_san_lost_spread.add_trace(go.Bar(name="Comp PF Paid", y=shared_y_branches, x=comp_pf_lost, orientation='h', marker_color="#9f1239", text=[f"{v}" if v > 0 else "" for v in comp_pf_lost], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))

        max_x = max(san_lost_totals) if len(san_lost_totals) > 0 else 100
        for i, branch in enumerate(shared_y_branches):
            if san_lost_totals[i] > 0:
                fig_san_lost_spread.add_annotation(x=san_lost_totals[i], y=branch, text=f"<span style='color:#64748b; font-size:11px; font-weight:normal;'>Lost Potential</span><br><b style='font-size:16px; color:#9f1239;'>⚠️ {san_potential_loss_pcts[i]}</b>", showarrow=False, xanchor="left", xshift=12, align="left")

        fig_san_lost_spread.update_layout(barmode="stack", height=350, margin=dict(t=20, b=20, l=10, r=90), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False, range=[0, max_x + (max_x*0.3)]), yaxis=dict(showticklabels=False, autorange="reversed"), showlegend=False)
        st.plotly_chart(fig_san_lost_spread, use_container_width=True)
