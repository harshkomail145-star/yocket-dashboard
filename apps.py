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

st.title("📊 Bank Operating System Fall 26")

# ==========================================
# 2. THE LIVE DATA PIPELINE ENGINE (V6 BUSTER)
# ==========================================
@st.cache_data
def process_lead_engine_v6(file):
    df = pd.read_csv(file)
    
    # CRITICAL FIX: Clean Column Names
    df.columns = df.columns.str.strip().str.lower()
    
    # Standardize Dates
    date_cols = ['date_shared', 'login_date', 'sanction_date', 'pf_date']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        else:
            df[col] = pd.NaT
            
    # Calculate TAT (Turnaround Time in Days)
    if 'date_shared' in df.columns and 'login_date' in df.columns:
        df['tat_bp_login'] = (df['login_date'] - df['date_shared']).dt.days
    if 'login_date' in df.columns and 'sanction_date' in df.columns:
        df['tat_login_sanc'] = (df['sanction_date'] - df['login_date']).dt.days
    if 'sanction_date' in df.columns and 'pf_date' in df.columns:
        df['tat_sanc_pf'] = (df['pf_date'] - df['sanction_date']).dt.days
    
    # Flight Risk Engine
    df['stage_val'] = 0
    if 'date_shared' in df.columns: df.loc[df['date_shared'].notnull(), 'stage_val'] = 1
    if 'login_date' in df.columns: df.loc[df['login_date'].notnull(), 'stage_val'] = 2
    if 'sanction_date' in df.columns: df.loc[df['sanction_date'].notnull(), 'stage_val'] = 3
    if 'pf_date' in df.columns: df.loc[df['pf_date'].notnull(), 'stage_val'] = 4
    
    if 'user_id' in df.columns:
        user_max_stage = df.groupby('user_id')['stage_val'].max()
        df['user_max_stage'] = df['user_id'].map(user_max_stage)
    else:
        df['user_max_stage'] = df['stage_val']
    
    return df

# ==========================================
# 3. GLOBAL FILTERS (SIDEBAR)
# ==========================================
with st.sidebar:
    st.header("⚙️ Global Controls")
    
    uploaded_file = st.file_uploader("Upload Yocket Lead CSV", type=["csv"])
    
    if uploaded_file is None:
        st.warning("⚠️ Waiting for data... Please upload your CSV to activate the dashboard.")
        st.stop()
        
    raw_df = process_lead_engine_v6(uploaded_file)
    
    if 'bank_name' in raw_df.columns:
        available_banks = raw_df['bank_name'].dropna().unique().tolist()
        selected_banks = st.multiselect("Select Bank Partners", available_banks, default=available_banks)
        df = raw_df[raw_df['bank_name'].isin(selected_banks)].copy()
    else:
        df = raw_df.copy()
    
    st.divider()
    st.caption("UI Mode: LIVE PANDAS ENGINE 🟢")

# ------------------------------------------
# CREATE OUR COHORT DATAFRAME
# ------------------------------------------
if 'cohort' in df.columns:
    df_cohort = df[
        df['cohort'].astype(str).str.contains('fall', case=False, na=False) & 
        df['cohort'].astype(str).str.contains('26', case=False, na=False)
    ].copy()
else:
    df_cohort = pd.DataFrame()

# Fallback: If no cohort matches, analyze entire file
if df_cohort.empty:
    df_cohort = df.copy()

tab_overall, tab_bp_login, tab_log_san, tab_san_pf = st.tabs([
    "🌐 Overall Performance", 
    "🔍 BP to Login",
    "📝 Login to Sanction",
    "✅ Sanction to PF"
])

# ==========================================
# TAB 1: OVERALL PERFORMANCE
# ==========================================
with tab_overall:
    st.markdown('<div class="section-header"><h2>📈 1. Y-o-Y Performance & Monthly Logins</h2></div>', unsafe_allow_html=True)
    st.text_area(label="Notes", placeholder="Type your insights, talking points, or action items here...", label_visibility="collapsed", key="note_yoy_metrics")

    today = pd.to_datetime('today')
    f26_start = pd.to_datetime(f"{today.year}-01-01")
    f26_end = today
    f25_start = pd.to_datetime(f"{today.year - 1}-01-01")
    f25_end = today.replace(year=today.year - 1)

    def count_ytd(dataframe, date_col, start_dt, end_dt):
        if date_col not in dataframe.columns: return 0
        return ((dataframe[date_col] >= start_dt) & (dataframe[date_col] <= end_dt)).sum()

    fall_26_data = [count_ytd(df, 'date_shared', f26_start, f26_end), count_ytd(df, 'login_date', f26_start, f26_end), count_ytd(df, 'sanction_date', f26_start, f26_end), count_ytd(df, 'pf_date', f26_start, f26_end)]
    fall_25_data = [count_ytd(df, 'date_shared', f25_start, f25_end), count_ytd(df, 'login_date', f25_start, f25_end), count_ytd(df, 'sanction_date', f25_start, f25_end), count_ytd(df, 'pf_date', f25_start, f25_end)]
    
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

        max_y_val = max(fall_26_data + fall_25_data) if (fall_26_data + fall_25_data) else 100
        
        growth_annotations = []
        for i, stage in enumerate(stages):
            y_max = max(fall_25_data[i], fall_26_data[i])
            icon = "⬇" if "-" in yoy_growth[i] else "⬆"
            if yoy_growth[i] != "N/A":
                growth_annotations.append(dict(
                    x=stage, 
                    y=y_max + (max_y_val * 0.18), 
                    text=f"<b>{icon} {yoy_growth[i]}</b><br><span style='font-size:11px'>YoY Growth</span>",
                    showarrow=False, font=dict(size=14, color="black"), bgcolor="#f8fafc", bordercolor="#94a3b8", borderwidth=1, borderpad=6
                ))

        fig_top_metrics.update_layout(barmode='group', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(gridcolor='#e2e8f0', range=[0, max_y_val * 1.45]), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5), annotations=growth_annotations, margin=dict(t=80))
        st.plotly_chart(fig_top_metrics, width="stretch")

    with col2:
        st.subheader("YoY Monthly Logins")
        df_logins_26 = df[(df['login_date'] >= f26_start) & (df['login_date'] <= f26_end)] if 'login_date' in df.columns else pd.DataFrame()
        df_logins_25 = df[(df['login_date'] >= f25_start) & (df['login_date'] <= f25_end)] if 'login_date' in df.columns else pd.DataFrame()
        
        f26_monthly = df_logins_26['login_date'].dt.month.value_counts().sort_index() if not df_logins_26.empty else {}
        f25_monthly = df_logins_25['login_date'].dt.month.value_counts().sort_index() if not df_logins_25.empty else {}
        
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

        max_y_log = max(fall_26_logins + fall_25_logins) if (fall_26_logins + fall_25_logins) else 100

        mom_annotations = []
        for i, month in enumerate(months_list):
            y_max = max(fall_26_logins[i], fall_25_logins[i])
            icon = "⬇" if "-" in mom_growth[i] else "⬆"
            if mom_growth[i] != "N/A":
                mom_annotations.append(dict(
                    x=month, 
                    y=y_max + (max_y_log * 0.18), 
                    text=f"<b>{icon} {mom_growth[i]}</b><br><span style='font-size:11px'>Growth</span>", 
                    showarrow=False, font=dict(size=13, color="black"), bgcolor="#f8fafc", bordercolor="#94a3b8", borderwidth=1, borderpad=6
                ))

        fig_yoy_bar.update_layout(barmode='group', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(gridcolor='#e2e8f0', range=[0, max_y_log * 1.45]), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5), annotations=mom_annotations, margin=dict(t=80))
        st.plotly_chart(fig_yoy_bar, width="stretch")
    
    st.divider()

    # --- SECTION 2: M-O-M PROGRESSION ---
    st.markdown('<div class="section-header"><h2>📅 2. Fall 26 M-o-M Progression by Stage</h2></div>', unsafe_allow_html=True)
    st.markdown("Tracking how the current Fall '26 pipeline is converting through all stages month-over-month.")
    
    def get_monthly_counts(date_series, max_month):
        if date_series.isnull().all(): return [0]*max_month
        counts = date_series.dt.month.value_counts().reindex(range(1, max_month + 1), fill_value=0)
        return counts.tolist()

    shared_mom = get_monthly_counts(df_cohort['date_shared'] if 'date_shared' in df_cohort.columns else pd.Series(dtype='datetime64[ns]'), current_month)
    login_mom = get_monthly_counts(df_cohort['login_date'] if 'login_date' in df_cohort.columns else pd.Series(dtype='datetime64[ns]'), current_month)
    sanc_mom = get_monthly_counts(df_cohort['sanction_date'] if 'sanction_date' in df_cohort.columns else pd.Series(dtype='datetime64[ns]'), current_month)
    pf_mom = get_monthly_counts(df_cohort['pf_date'] if 'pf_date' in df_cohort.columns else pd.Series(dtype='datetime64[ns]'), current_month)

    fig_mom = go.Figure()
    fig_mom.add_trace(go.Bar(name='Shared', x=months_list, y=shared_mom, marker_color='#a78bfa', text=shared_mom, textposition='outside'))
    fig_mom.add_trace(go.Bar(name='Login', x=months_list, y=login_mom, marker_color='#fda4af', text=login_mom, textposition='outside'))
    fig_mom.add_trace(go.Bar(name='Sanction', x=months_list, y=sanc_mom, marker_color='#fef08a', text=sanc_mom, textposition='outside'))
    fig_mom.add_trace(go.Bar(name='PF Paid', x=months_list, y=pf_mom, marker_color='#a7f3d0', text=pf_mom, textposition='outside'))

    fig_mom.update_traces(textfont=dict(size=12, color="black"))
    max_mom_val = max(shared_mom) if shared_mom else 100
    fig_mom.update_layout(barmode='group', height=380, margin=dict(t=40, b=20, l=20, r=20), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', yaxis=dict(gridcolor='#e2e8f0', range=[0, max_mom_val * 1.2]), legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5, title=None))
    st.plotly_chart(fig_mom, width="stretch")

    st.divider()

    # --- SECTION 3: SHARED LEAD COHORT FUNNEL ---
    st.markdown('<div class="section-header"><h2>🧬 3. Shared Leads Pipeline (Fall 26 Cohort)</h2></div>', unsafe_allow_html=True)
    st.markdown("Left-to-Right pipeline tracking active volumes, drop-offs, and true stage-to-stage conversion. <br><span style='color:#a7f3d0; font-size:18px'>●</span> <b>Current (Active)</b> &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#fca5a5; font-size:18px'>●</span> <b>Lost (Dropped)</b>", unsafe_allow_html=True)
    
    tot_shared = df_cohort['date_shared'].notnull().sum() if 'date_shared' in df_cohort.columns else 0
    tot_login = df_cohort['login_date'].notnull().sum() if 'login_date' in df_cohort.columns else 0
    tot_sanc = df_cohort['sanction_date'].notnull().sum() if 'sanction_date' in df_cohort.columns else 0
    tot_pf = df_cohort['pf_date'].notnull().sum() if 'pf_date' in df_cohort.columns else 0
    totals = [tot_shared, tot_login, tot_sanc, tot_pf]
    
    curr_bp = df_cohort[df_cohort['lender_stage'] == 'Bank Prospect'].shape[0] if 'lender_stage' in df_cohort.columns else 0
    curr_log = df_cohort[df_cohort['lender_stage'] == 'Login'].shape[0] if 'lender_stage' in df_cohort.columns else 0
    curr_san = df_cohort[df_cohort['lender_stage'] == 'Sanction'].shape[0] if 'lender_stage' in df_cohort.columns else 0
    currents = [curr_bp, curr_log, curr_san, tot_pf] 

    if 'lost_category' in df_cohort.columns:
        lost_bp_funnel = df_cohort[df_cohort['lost_category'].astype(str).str.contains('BP', case=False, na=False)].shape[0]
        lost_log_funnel = df_cohort[df_cohort['lost_category'].astype(str).str.contains('Login', case=False, na=False)].shape[0]
        lost_san_funnel = df_cohort[df_cohort['lost_category'].astype(str).str.contains('Sanction', case=False, na=False)].shape[0]
    else:
        lost_bp_funnel, lost_log_funnel, lost_san_funnel = 0, 0, 0
    losts = [lost_bp_funnel, lost_log_funnel, lost_san_funnel, 0]
    
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
    st.plotly_chart(fig_funnel, width="stretch")

    st.divider()

    # -------------------------------------------------------------
    # --- DATA PREP FOR SECTIONS 4, 5, 6, 7 (NO MORE NAME ERRORS) ---
    # -------------------------------------------------------------
    active_bp = df_cohort[df_cohort['lender_stage'] == 'Bank Prospect'].copy() if 'lender_stage' in df_cohort.columns else pd.DataFrame()
    active_log = df_cohort[df_cohort['lender_stage'] == 'Login'].copy() if 'lender_stage' in df_cohort.columns else pd.DataFrame()
    active_san = df_cohort[df_cohort['lender_stage'] == 'Sanction'].copy() if 'lender_stage' in df_cohort.columns else pd.DataFrame()
    
    if 'lost_category' in df_cohort.columns:
        lost_bp_df = df_cohort[df_cohort['lost_category'].astype(str).str.contains('BP', case=False, na=False)]
        lost_log_df = df_cohort[df_cohort['lost_category'].astype(str).str.contains('Login', case=False, na=False)]
        lost_san_df = df_cohort[df_cohort['lost_category'].astype(str).str.contains('Sanction', case=False, na=False)]
    else:
        lost_bp_df = lost_log_df = lost_san_df = pd.DataFrame()

    # --- SECTION 4: ACTIVE PIPELINE HEALTH ---
    st.markdown('<div class="section-header"><h2>⏱️ 4. Active Pipeline Health</h2></div>', unsafe_allow_html=True)
    st.markdown("A macro view of your active pipeline. Breaking down healthy leads vs. aging bottlenecks vs. competitor leakage.")

    stages_health = [f"<b>BP Stage</b><br>{active_bp.shape[0]} Active Leads", f"<b>Login Stage</b><br>{active_log.shape[0]} Active Leads", f"<b>Sanction Stage</b><br>{active_san.shape[0]} Active Leads"]

    # 1. TERMINAL LOSS: Only leads that PAID PF to a competitor are removed
    comp_vals = [
        active_bp[active_bp['user_max_stage'] == 4].shape[0] if not active_bp.empty else 0, 
        active_log[active_log['user_max_stage'] == 4].shape[0] if not active_log.empty else 0, 
        active_san[active_san['user_max_stage'] == 4].shape[0] if not active_san.empty else 0
    ]

    # 2. HEALTHY WORKABLE (< 7 Days AND hasn't paid PF elsewhere)
    under_7_vals = [
        active_bp[(pd.to_datetime('today') - active_bp['date_shared']).dt.days.lt(7) & (active_bp['user_max_stage'] < 4)].shape[0] if not active_bp.empty and 'date_shared' in active_bp else 0, 
        active_log[(pd.to_datetime('today') - active_log['login_date']).dt.days.lt(7) & (active_log['user_max_stage'] < 4)].shape[0] if not active_log.empty and 'login_date' in active_log else 0, 
        active_san[(pd.to_datetime('today') - active_san['sanction_date']).dt.days.lt(7) & (active_san['user_max_stage'] < 4)].shape[0] if not active_san.empty and 'sanction_date' in active_san else 0
    ]
    
    # 3. AGING WORKABLE (> 7 Days AND hasn't paid PF elsewhere)
    over_7_vals = [
        active_bp[(pd.to_datetime('today') - active_bp['date_shared']).dt.days.ge(7) & (active_bp['user_max_stage'] < 4)].shape[0] if not active_bp.empty and 'date_shared' in active_bp else 0, 
        active_log[(pd.to_datetime('today') - active_log['login_date']).dt.days.ge(7) & (active_log['user_max_stage'] < 4)].shape[0] if not active_log.empty and 'login_date' in active_log else 0, 
        active_san[(pd.to_datetime('today') - active_san['sanction_date']).dt.days.ge(7) & (active_san['user_max_stage'] < 4)].shape[0] if not active_san.empty and 'sanction_date' in active_san else 0
    ]

    totals_health = [u + o + c for u, o, c in zip(under_7_vals, over_7_vals, comp_vals)]
    
    under_7_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(under_7_vals, totals_health)]
    over_7_pct_num  = [(v/t)*100 if t > 0 else 0 for v, t in zip(over_7_vals, totals_health)]
    comp_pct_num    = [(v/t)*100 if t > 0 else 0 for v, t in zip(comp_vals, totals_health)]

    under_7_labels = [f"{p:.0f}%" if p > 0 else "" for p in under_7_pct_num]
    over_7_labels  = [f"{p:.0f}%" if p > 0 else "" for p in over_7_pct_num]
    comp_labels    = [f"{p:.0f}%" if p > 0 else "" for p in comp_pct_num]

    fig_health_bar = go.Figure()
    fig_health_bar.add_trace(go.Bar(name="< 7 Days (Active)", y=stages_health, x=under_7_pct_num, orientation='h', marker_color="#a7f3d0", text=under_7_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="#0f172a", weight="bold")))
    fig_health_bar.add_trace(go.Bar(name="> 7 Days (Aging)", y=stages_health, x=over_7_pct_num, orientation='h', marker_color="#fed7aa", text=over_7_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="#0f172a", weight="bold")))
    fig_health_bar.add_trace(go.Bar(name="Terminal Loss to Competitor", y=stages_health, x=comp_pct_num, orientation='h', marker_color="#9f1239", text=comp_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))

    fig_health_bar.update_layout(barmode="stack", height=320, margin=dict(t=40, b=20, l=20, r=20), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]), yaxis=dict(showgrid=False, tickfont=dict(size=15, color="#1e293b"), autorange="reversed"))
    st.plotly_chart(fig_health_bar, width="stretch")

    st.divider()

    # --- SECTION 5: LOSING THE ACTIVE PROSPECTS ---
    st.markdown('<div class="section-header"><h2>💸 5. Losing The Active Prospects</h2></div>', unsafe_allow_html=True)
    st.markdown("Where our workable leads are currently sitting (Exclusive vs. Flight Risk).")

    # 1. DEFINE WORKABLE LEADS (Active minus Terminal Loss to Competitor)
    workable_log = active_log[active_log['user_max_stage'] < 4] if not active_log.empty else pd.DataFrame()
    workable_bp = active_bp[active_bp['user_max_stage'] < 4] if not active_bp.empty else pd.DataFrame()

    stages_loss = [f"<b>Login Stage</b><br>{workable_log.shape[0]} Workable Leads", f"<b>BP Stage</b><br>{workable_bp.shape[0]} Workable Leads"]

    # 2. DISTRIBUTE THE WORKABLE LEADS
    exc_vals = [
        workable_log[workable_log['user_max_stage'] <= 2].shape[0] if not workable_log.empty else 0, 
        workable_bp[workable_bp['user_max_stage'] == 1].shape[0] if not workable_bp.empty else 0
    ]
    clog_vals = [
        0, 
        workable_bp[workable_bp['user_max_stage'] == 2].shape[0] if not workable_bp.empty else 0
    ]
    csan_vals = [
        workable_log[workable_log['user_max_stage'] == 3].shape[0] if not workable_log.empty else 0, 
        workable_bp[workable_bp['user_max_stage'] == 3].shape[0] if not workable_bp.empty else 0
    ]
    
    totals_loss = [workable_log.shape[0], workable_bp.shape[0]]

    exc_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(exc_vals, totals_loss)]
    clog_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(clog_vals, totals_loss)]
    csan_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(csan_vals, totals_loss)]

    exc_labels = [f"{p:.0f}%" if p > 0 else "" for p in exc_pct_num]
    clog_labels = [f"{p:.0f}%" if p > 0 else "" for p in clog_pct_num]
    csan_labels = [f"{p:.0f}%" if p > 0 else "" for p in csan_pct_num]

    fig_loss_bar = go.Figure()
    fig_loss_bar.add_trace(go.Bar(name="✅ Exclusive (Safe)", y=stages_loss, x=exc_pct_num, orientation='h', marker_color="#a7f3d0", text=exc_labels, textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="#0f172a")))
    fig_loss_bar.add_trace(go.Bar(name="⚠️ In Competitor Login", y=stages_loss, x=clog_pct_num, orientation='h', marker_color="#fed7aa", text=clog_labels, textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="#0f172a")))
    fig_loss_bar.add_trace(go.Bar(name="🚨 In Competitor Sanction", y=stages_loss, x=csan_pct_num, orientation='h', marker_color="#9f1239", text=csan_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))

    fig_loss_bar.update_layout(barmode="stack", height=280, margin=dict(t=40, b=20, l=20, r=20), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]), yaxis=dict(showgrid=False, tickfont=dict(size=15, color="#1e293b")))
    st.plotly_chart(fig_loss_bar, width="stretch")

    st.divider()

    # --- SECTION 6: LOST POTENTIAL ANALYSIS ---
    st.markdown('<div class="section-header"><h2>🚨 6. Lost Potential Analysis</h2></div>', unsafe_allow_html=True)
    st.subheader("Flight Risk: Where are they in the Competitor's Funnel?")
    st.markdown("Out of the total files lost at each stage, this tracks how many went to a competitor and **exactly what stage the competitor has reached with them**.")

    stages_lost = [f"<b>Lost from Sanction</b><br>({lost_san_df.shape[0]} Total)", f"<b>Lost from Login</b><br>({lost_log_df.shape[0]} Total)", f"<b>Lost from BP</b><br>({lost_bp_df.shape[0]} Total)"]
    bar_totals = [lost_san_df.shape[0], lost_log_df.shape[0], lost_bp_df.shape[0]]

    true_dead = [
        lost_san_df[lost_san_df['user_max_stage'] <= 3].shape[0] if not lost_san_df.empty else 0, 
        lost_log_df[lost_log_df['user_max_stage'] <= 2].shape[0] if not lost_log_df.empty else 0, 
        lost_bp_df[lost_bp_df['user_max_stage'] == 1].shape[0] if not lost_bp_df.empty else 0
    ]
    comp_login = [0, 0, lost_bp_df[lost_bp_df['user_max_stage'] == 2].shape[0] if not lost_bp_df.empty else 0]
    comp_sanc = [
        0, 
        lost_log_df[lost_log_df['user_max_stage'] == 3].shape[0] if not lost_log_df.empty else 0, 
        lost_bp_df[lost_bp_df['user_max_stage'] == 3].shape[0] if not lost_bp_df.empty else 0
    ]
    comp_pf = [
        lost_san_df[lost_san_df['user_max_stage'] == 4].shape[0] if not lost_san_df.empty else 0, 
        lost_log_df[lost_log_df['user_max_stage'] == 4].shape[0] if not lost_log_df.empty else 0, 
        lost_bp_df[lost_bp_df['user_max_stage'] == 4].shape[0] if not lost_bp_df.empty else 0
    ]

    # Calculate raw percentages for 100% stacked bars
    true_dead_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(true_dead, bar_totals)]
    comp_login_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(comp_login, bar_totals)]
    comp_sanc_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(comp_sanc, bar_totals)]
    comp_pf_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(comp_pf, bar_totals)]

    # Format text labels for the inside of the bars
    true_dead_labels = [f"{p:.0f}%" if p > 0 else "" for p in true_dead_pct_num]
    comp_login_labels = [f"{p:.0f}%" if p > 0 else "" for p in comp_login_pct_num]
    comp_sanc_labels = [f"{p:.0f}%" if p > 0 else "" for p in comp_sanc_pct_num]
    comp_pf_labels = [f"{p:.0f}%" if p > 0 else "" for p in comp_pf_pct_num]

    # Overall lost potential annotation
    potential_loss_pcts = [f"{((t - td) / t) * 100:.1f}%" if t > 0 else "0%" for t, td in zip(bar_totals, true_dead)]

    fig_flight = go.Figure()
    fig_flight.add_trace(go.Bar(name="True Dead (No Competitor Action)", y=stages_lost, x=true_dead_pct_num, orientation='h', marker_color="#e2e8f0", text=true_dead_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")))
    fig_flight.add_trace(go.Bar(name="In Competitor Login", y=stages_lost, x=comp_login_pct_num, orientation='h', marker_color="#fdba74", text=comp_login_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="#9a3412", weight="bold")))
    fig_flight.add_trace(go.Bar(name="In Competitor Sanction", y=stages_lost, x=comp_sanc_pct_num, orientation='h', marker_color="#f97316", text=comp_sanc_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))
    fig_flight.add_trace(go.Bar(name="Competitor PF Paid (Fully Lost)", y=stages_lost, x=comp_pf_pct_num, orientation='h', marker_color="#9f1239", text=comp_pf_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))

    # Append annotations perfectly to the end of the 100% bar
    for i, stage in enumerate(stages_lost):
        if bar_totals[i] > 0:
            fig_flight.add_annotation(x=100, y=stage, text=f"<span style='color:#64748b; font-size:11px; font-weight:normal;'>Lost Potential</span><br><b style='font-size:16px; color:#9f1239;'>⚠️ {potential_loss_pcts[i]}</b>", showarrow=False, xanchor="left", xshift=15, align="left")

    # Locked X-axis to 100 (plus 25 padding for the text annotation to fit)
    fig_flight.update_layout(barmode="stack", height=320, margin=dict(t=40, b=20, l=20, r=100), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False, range=[0, 125]), yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b")))
    st.plotly_chart(fig_flight, width="stretch")

    st.divider()

    # --- SECTION 7: REASON FOR POTENTIAL LOSS MATRIX ---
    st.subheader("Reason for Potential Loss (Flight Risk Leads Only)")
    st.markdown("Top reasons tagged by our team for leads that were marked 'Lost', but **actually progressed further with a competitor**.")
    
    # THE NEW MASTER LEGEND
    st.markdown("<p style='text-align: center; font-size:15px;'><span style='color:#fdba74'>■</span> <b>In Comp Login</b> &nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp; <span style='color:#f97316'>■</span> <b>In Comp Sanction</b> &nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp; <span style='color:#9f1239'>■</span> <b>Competitor PF Paid</b></p>", unsafe_allow_html=True)
    
    col_r1, col_r2, col_r3 = st.columns(3)

    def get_potential_loss_reasons(df_lost, base_stage_val):
        if df_lost.empty or 'lost_reason' not in df_lost.columns:
            return go.Figure()
        
        # 1. Filter ONLY to Potential Losses (Competitor progressed further than base stage)
        df_pot = df_lost[df_lost['user_max_stage'] > base_stage_val].copy()
        
        if df_pot.empty:
            # Return placeholder if there are no flight risk leads here
            fig = go.Figure()
            fig.update_layout(height=280, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False), yaxis=dict(visible=False), annotations=[dict(text="No Flight Risk Leads", showarrow=False, font=dict(size=16, color="#cbd5e1"))])
            return fig

        # 2. Get top 5 reasons by volume
        top_reasons = df_pot['lost_reason'].value_counts().head(5).index.tolist()
        df_top = df_pot[df_pot['lost_reason'].isin(top_reasons)]

        # 3. Group by reason and the competitor's stage
        grouped = df_top.groupby(['lost_reason', 'user_max_stage']).size().unstack(fill_value=0)
        grouped = grouped.reindex(top_reasons[::-1]) # Reverse to show largest on top in horizontal bar

        fig = go.Figure()
        
        # Map columns to the exact colors used in the Flight Risk chart above
        stage_colors = {
            2: {"name": "Comp Login", "color": "#fdba74", "text_color": "#9a3412"},
            3: {"name": "Comp Sanction", "color": "#f97316", "text_color": "white"},
            4: {"name": "Comp PF Paid", "color": "#9f1239", "text_color": "white"}
        }

        # Build the stacked bars
        for stage_val in [2, 3, 4]:
            if stage_val in grouped.columns and stage_val > base_stage_val:
                fig.add_trace(go.Bar(
                    name=stage_colors[stage_val]["name"], 
                    y=grouped.index, 
                    x=grouped[stage_val], 
                    orientation='h', 
                    marker_color=stage_colors[stage_val]["color"], 
                    text=[f"{v}" if v > 0 else "" for v in grouped[stage_val]], 
                    textposition='inside', 
                    insidetextanchor='middle',
                    textfont=dict(color=stage_colors[stage_val]["text_color"], weight="bold")
                ))

        # Add total annotation at the end of each stacked bar
        totals = grouped.sum(axis=1)
        for i, reason in enumerate(grouped.index):
            if totals[reason] > 0:
                fig.add_annotation(x=totals[reason], y=reason, text=f"<b>{int(totals[reason])}</b>", showarrow=False, xanchor="left", xshift=5, font=dict(color="#1e293b", size=13))

        max_x = max(totals) if not totals.empty else 10
        fig.update_layout(
            barmode="stack", 
            height=280, 
            margin=dict(t=20, b=20, l=10, r=40), 
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)', 
            xaxis=dict(showgrid=False, showticklabels=False, range=[0, max_x + (max_x * 0.2)]), 
            yaxis=dict(showgrid=False, tickfont=dict(weight="bold", color="#475569")),
            showlegend=False
        )
        return fig

    with col_r1:
        st.markdown("**1. Lost from BP Stage**")
        st.plotly_chart(get_potential_loss_reasons(lost_bp_df, 1), width="stretch")

    with col_r2:
        st.markdown("**2. Lost from Login Stage**")
        st.plotly_chart(get_potential_loss_reasons(lost_log_df, 2), width="stretch")

    with col_r3:
        st.markdown("**3. Lost from Sanction Stage**")
        st.plotly_chart(get_potential_loss_reasons(lost_san_df, 3), width="stretch")
# ==========================================
# TAB 2: BP TO LOGIN DEEP DIVE
# ==========================================
with tab_bp_login:
    bp_df = df_cohort[df_cohort['date_shared'].notnull()] if 'date_shared' in df_cohort.columns else pd.DataFrame()
    
    if not bp_df.empty and 'location' in bp_df.columns:
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
                    st.metric(label=f"📍 {top_branches[i]}", value=f"{bp_vols[i]:,}", delta=f"{bp_pcts[i]} Share", delta_color="off")
        st.divider()

        # --- DATA ENGINE FOR TAB 2 ---
        conv_rates, tat_days = [], []
        active_bp_counts, lost_bp_counts = [], []
        bp_u7_vals, bp_o7_vals, bp_term_vals = [], [], []

        active_bp_df = bp_df[bp_df['lender_stage'] == 'Bank Prospect'].copy() if 'lender_stage' in bp_df.columns else pd.DataFrame()
        if not active_bp_df.empty and 'date_shared' in active_bp_df.columns:
            active_bp_df['aging_days'] = (pd.to_datetime('today') - active_bp_df['date_shared']).dt.days
        else:
            active_bp_df['aging_days'] = 0
            
        lost_bp_df = bp_df[bp_df['lost_category'].astype(str).str.contains('BP', case=False, na=False)] if 'lost_category' in bp_df.columns else pd.DataFrame()

        for b in shared_y_branches:
            b_df = bp_df[bp_df['location'] == b]
            shared_c = b_df.shape[0]
            log_c = b_df['login_date'].notnull().sum() if 'login_date' in b_df.columns else 0
            
            conv_rates.append(round((log_c/shared_c)*100, 1) if shared_c > 0 else 0)
            tat_days.append(round(b_df['tat_bp_login'].mean(), 1) if not b_df.empty and 'tat_bp_login' in b_df.columns and not pd.isna(b_df['tat_bp_login'].mean()) else 0)
            
            b_act = active_bp_df[active_bp_df['location'] == b] if not active_bp_df.empty else pd.DataFrame()
            b_lost = lost_bp_df[lost_bp_df['location'] == b] if not lost_bp_df.empty else pd.DataFrame()
            
            active_bp_counts.append(b_act.shape[0])
            lost_bp_counts.append(b_lost.shape[0])
            
            # 100% Mutually Exclusive Pipeline Health Math
            u7 = b_act[(b_act['aging_days'] < 7) & (b_act['user_max_stage'] < 4)].shape[0] if not b_act.empty else 0
            o7 = b_act[(b_act['aging_days'] >= 7) & (b_act['user_max_stage'] < 4)].shape[0] if not b_act.empty else 0
            term = b_act[b_act['user_max_stage'] == 4].shape[0] if not b_act.empty else 0
            
            bp_u7_vals.append(u7)
            bp_o7_vals.append(o7)
            bp_term_vals.append(term)

        # --- ROW 1: CONVERSION, TAT & VOLUMES (4-COLUMN GRID) ---
        st.markdown('<div class="section-header"><h2>📊 1. Branch Performance Matrix</h2></div>', unsafe_allow_html=True)
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        
        with col_c1:
            tot_s = bp_df.shape[0] if not bp_df.empty else 0
            tot_l = bp_df['login_date'].notnull().sum() if not bp_df.empty and 'login_date' in bp_df.columns else 0
            lender_avg_conv = round((tot_l / tot_s)*100, 1) if tot_s > 0 else 0
            
            st.markdown(f"<div style='min-height: 80px;'><h4 style='text-align: center; margin-bottom:0px; color: #475569;'>BP ➔ Login Rate<br><span style='font-size:14px; font-weight:normal;'>(Lender Avg: {lender_avg_conv}%)</span></h4></div>", unsafe_allow_html=True)
            conv_colors = ["#9f1239" if val < lender_avg_conv else "#cbd5e1" for val in conv_rates]
            fig_conv = go.Figure(go.Bar(y=shared_y_branches, x=conv_rates, orientation='h', marker_color=conv_colors, text=[f"{v}%" for v in conv_rates], textposition="inside", insidetextanchor="middle", textfont=dict(color=["white" if c == "#9f1239" else "#0f172a" for c in conv_colors], weight="bold")))
            fig_conv.add_vline(x=lender_avg_conv, line_dash="dash", line_color="#475569", line_width=2)
            fig_conv.update_layout(height=320, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569")))
            st.plotly_chart(fig_conv, width="stretch")

        with col_c2:
            # Dynamically calculate the TAT average for the selected lender(s)
            lender_avg_tat = round(bp_df['tat_bp_login'].mean(), 1) if not bp_df.empty and 'tat_bp_login' in bp_df.columns and not pd.isna(bp_df['tat_bp_login'].mean()) else 0
            
            st.markdown(f"<div style='min-height: 80px;'><h4 style='text-align: center; margin-bottom:0px; color: #475569;'>BP ➔ Login TAT<br><span style='font-size:14px; font-weight:normal;'>(Lender Avg: {lender_avg_tat} Days)</span></h4></div>", unsafe_allow_html=True)
            tat_colors = ["#9f1239" if val > lender_avg_tat else "#cbd5e1" for val in tat_days]
            fig_tat = go.Figure(go.Bar(y=shared_y_branches, x=tat_days, orientation='h', marker_color=tat_colors, text=[f"{v} days" for v in tat_days], textposition="inside", insidetextanchor="middle", textfont=dict(color=["white" if c == "#9f1239" else "#0f172a" for c in tat_colors], weight="bold")))
            fig_tat.add_vline(x=lender_avg_tat, line_dash="dash", line_color="#475569", line_width=2)
            fig_tat.update_layout(height=320, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
            st.plotly_chart(fig_tat, width="stretch")

        with col_c3:
            st.markdown("<div style='min-height: 80px;'><h4 style='text-align: center; margin-bottom:0px; color: #475569;'>Current Active Leads<br><span style='font-size:14px; font-weight:normal;'>(Sitting in BP Stage)</span></h4></div>", unsafe_allow_html=True)
            fig_act = go.Figure(go.Bar(y=shared_y_branches, x=active_bp_counts, orientation='h', marker_color="#3b82f6", text=[f"{v}" for v in active_bp_counts], textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="white")))
            fig_act.update_layout(height=320, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
            st.plotly_chart(fig_act, width="stretch")

        with col_c4:
            st.markdown("<div style='min-height: 80px;'><h4 style='text-align: center; margin-bottom:0px; color: #475569;'>Total Lost Leads<br><span style='font-size:14px; font-weight:normal;'>(Lost from BP Stage)</span></h4></div>", unsafe_allow_html=True)
            fig_lst = go.Figure(go.Bar(y=shared_y_branches, x=lost_bp_counts, orientation='h', marker_color="#ef4444", text=[f"{v}" for v in lost_bp_counts], textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="white")))
            fig_lst.update_layout(height=320, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
            st.plotly_chart(fig_lst, width="stretch")
        st.divider()

        # --- ROW 2: ACTIVE PIPELINE HEALTH (BRANCH-WISE 100% STACKED) ---
        st.markdown('<div class="section-header"><h2>⏱️ 2. Active Pipeline Health (Branch-wise)</h2></div>', unsafe_allow_html=True)
        st.markdown("A macro view of your **Active** pipeline. Breaking down healthy leads vs. aging bottlenecks vs. competitor leakage.")

        totals_health_bp = [u + o + c for u, o, c in zip(bp_u7_vals, bp_o7_vals, bp_term_vals)]
        branch_health_labels = [f"<b>{b}</b><br>{t} Active" for b, t in zip(shared_y_branches, totals_health_bp)]

        u7_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(bp_u7_vals, totals_health_bp)]
        o7_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(bp_o7_vals, totals_health_bp)]
        term_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(bp_term_vals, totals_health_bp)]

        u7_labels = [f"{p:.0f}%" if p > 0 else "" for p in u7_pct_num]
        o7_labels = [f"{p:.0f}%" if p > 0 else "" for p in o7_pct_num]
        term_labels = [f"{p:.0f}%" if p > 0 else "" for p in term_pct_num]

        fig_health_bp = go.Figure()
        fig_health_bp.add_trace(go.Bar(name="< 7 Days (Active)", y=branch_health_labels, x=u7_pct_num, orientation='h', marker_color="#a7f3d0", text=u7_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="#0f172a", weight="bold")))
        fig_health_bp.add_trace(go.Bar(name="> 7 Days (Aging)", y=branch_health_labels, x=o7_pct_num, orientation='h', marker_color="#fed7aa", text=o7_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="#0f172a", weight="bold")))
        fig_health_bp.add_trace(go.Bar(name="Terminal Loss to Competitor", y=branch_health_labels, x=term_pct_num, orientation='h', marker_color="#9f1239", text=term_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))

        fig_health_bp.update_layout(barmode="stack", height=380, margin=dict(t=40, b=20, l=20, r=20), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]), yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b"), autorange="reversed"))
        st.plotly_chart(fig_health_bp, width="stretch")
        st.divider()
        # --- ROW 3: LOSING THE ACTIVE PROSPECTS (BRANCH-WISE 100% STACKED) ---
        st.markdown('<div class="section-header"><h2>💸 3. Losing The Active Prospects (Branch-wise)</h2></div>', unsafe_allow_html=True)
        st.markdown("Where our **Workable** BP leads are currently sitting (Exclusive vs. Flight Risk).")

        bp_exc_vals = []
        bp_clog_vals = []
        bp_csan_vals = []
        bp_workable_totals = []

        for b in shared_y_branches:
            # Get active leads for this branch
            b_act = active_bp_df[(active_bp_df['location'] == b)] if not active_bp_df.empty else pd.DataFrame()
            
            # Filter to strictly WORKABLE leads (exclude Terminal Loss / Stage 4)
            b_workable = b_act[b_act['user_max_stage'] < 4] if not b_act.empty else pd.DataFrame()
            
            bp_workable_totals.append(b_workable.shape[0])
            bp_exc_vals.append(b_workable[b_workable['user_max_stage'] == 1].shape[0] if not b_workable.empty else 0)
            bp_clog_vals.append(b_workable[b_workable['user_max_stage'] == 2].shape[0] if not b_workable.empty else 0)
            bp_csan_vals.append(b_workable[b_workable['user_max_stage'] == 3].shape[0] if not b_workable.empty else 0)

        # Update Y-Axis labels to show the Workable base
        branch_loss_labels = [f"<b>{b}</b><br>{t} Workable" for b, t in zip(shared_y_branches, bp_workable_totals)]

        # Convert to 100% scale
        exc_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(bp_exc_vals, bp_workable_totals)]
        clog_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(bp_clog_vals, bp_workable_totals)]
        csan_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(bp_csan_vals, bp_workable_totals)]

        exc_labels = [f"{p:.0f}%" if p > 0 else "" for p in exc_pct_num]
        clog_labels = [f"{p:.0f}%" if p > 0 else "" for p in clog_pct_num]
        csan_labels = [f"{p:.0f}%" if p > 0 else "" for p in csan_pct_num]

        fig_loss_bp = go.Figure()
        fig_loss_bp.add_trace(go.Bar(name="✅ Exclusive (Safe)", y=branch_loss_labels, x=exc_pct_num, orientation='h', marker_color="#a7f3d0", text=exc_labels, textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="#0f172a")))
        fig_loss_bp.add_trace(go.Bar(name="⚠️ In Competitor Login", y=branch_loss_labels, x=clog_pct_num, orientation='h', marker_color="#fed7aa", text=clog_labels, textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="#0f172a")))
        fig_loss_bp.add_trace(go.Bar(name="🚨 In Competitor Sanction", y=branch_loss_labels, x=csan_pct_num, orientation='h', marker_color="#9f1239", text=csan_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))

        fig_loss_bp.update_layout(barmode="stack", height=380, margin=dict(t=40, b=20, l=20, r=20), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]), yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b"), autorange="reversed"))
        st.plotly_chart(fig_loss_bp, width="stretch")
        
        st.divider()

# ==========================================
# TAB 3: LOGIN TO SANCTION DEEP DIVE
# ==========================================
with tab_log_san:
    log_df = df_cohort[df_cohort['login_date'].notnull()] if 'login_date' in df_cohort.columns else pd.DataFrame()
    
    if not log_df.empty and 'location' in log_df.columns:
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

        st.markdown('<div class="section-header"><h2>🗂️ Login Distribution</h2></div>', unsafe_allow_html=True)
        card_cols = st.columns(6)
        for i, col in enumerate(card_cols):
            if i < len(top_branches):
                with col:
                    st.metric(label=f"📍 {top_branches[i]}", value=f"{log_vols[i]:,}", delta=f"{log_pcts[i]} Share", delta_color="off")
        st.divider()

        conv_rates, tat_days, true_active_log, paid_comp_log = [], [], [], []
        log_under_7, log_over_7 = [], []
        log_exclusive, log_comp_sanc = [], []

        active_log_df = log_df[log_df['lender_stage'] == 'Login'].copy() if 'lender_stage' in log_df.columns else pd.DataFrame()
        if not active_log_df.empty and 'login_date' in active_log_df.columns:
            active_log_df['aging_days'] = (pd.to_datetime('today') - active_log_df['login_date']).dt.days
        else:
            active_log_df['aging_days'] = 0

        for b in shared_y_branches:
            b_df = log_df[log_df['location'] == b]
            log_c = b_df.shape[0]
            san_c = b_df['sanction_date'].notnull().sum() if 'sanction_date' in b_df.columns else 0
            
            conv_rates.append(round((san_c/log_c)*100, 1) if log_c > 0 else 0)
            tat_days.append(round(b_df['tat_login_sanc'].mean(), 1) if not b_df.empty and 'tat_login_sanc' in b_df.columns and not pd.isna(b_df['tat_login_sanc'].mean()) else 0)
            
            b_act = active_log_df[active_log_df['location'] == b] if 'location' in active_log_df.columns else pd.DataFrame()
            true_active_log.append(b_act[b_act['user_max_stage'] < 4].shape[0] if not b_act.empty else 0) 
            paid_comp_log.append(b_act[b_act['user_max_stage'] == 4].shape[0] if not b_act.empty else 0)  
            
            log_under_7.append(b_act[b_act['aging_days'] < 7].shape[0] if not b_act.empty else 0)
            log_over_7.append(b_act[b_act['aging_days'] >= 7].shape[0] if not b_act.empty else 0)
            
            log_exclusive.append(b_act[b_act['user_max_stage'] <= 2].shape[0] if not b_act.empty else 0)
            log_comp_sanc.append(b_act[b_act['user_max_stage'] == 3].shape[0] if not b_act.empty else 0)

        st.markdown('<div class="section-header"><h2>📊 1. Conversion, Aging & Immediate Flight Risk</h2></div>', unsafe_allow_html=True)
        col_c1, col_c2, col_c3 = st.columns(3)
        
        with col_c1:
            tot_l = df_cohort['login_date'].notnull().sum() if 'login_date' in df_cohort.columns else 0
            tot_s = df_cohort['sanction_date'].notnull().sum() if 'sanction_date' in df_cohort.columns else 0
            nat_avg = round((tot_s / tot_l)*100, 1) if tot_l > 0 else 0
            
            st.markdown(f"<div style='min-height: 80px;'><h4 style='text-align: center; margin-bottom:0px; color: #475569;'>Login ➔ Sanction Rate<br><span style='font-size:14px; font-weight:normal;'>(Nat. Avg: {nat_avg}%)</span></h4></div>", unsafe_allow_html=True)
            conv_colors = ["#9f1239" if val < nat_avg else "#cbd5e1" for val in conv_rates]
            fig_conv = go.Figure(go.Bar(y=shared_y_branches, x=conv_rates, orientation='h', marker_color=conv_colors, text=[f"{v}%" for v in conv_rates], textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold")))
            fig_conv.add_vline(x=nat_avg, line_dash="dash", line_color="#475569", line_width=2)
            fig_conv.update_layout(height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569")))
            st.plotly_chart(fig_conv, width="stretch")

        with col_c2:
            target_tat = 7.0
            st.markdown(f"<div style='min-height: 80px;'><h4 style='text-align: center; margin-bottom:0px; color: #475569;'>Login ➔ Sanction TAT<br><span style='font-size:14px; font-weight:normal;'>(Target SLA: {target_tat} Days)</span></h4></div>", unsafe_allow_html=True)
            tat_colors = ["#9f1239" if val > target_tat else "#cbd5e1" for val in tat_days]
            fig_tat = go.Figure(go.Bar(y=shared_y_branches, x=tat_days, orientation='h', marker_color=tat_colors, text=[f"{v} days" for v in tat_days], textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold")))
            fig_tat.add_vline(x=target_tat, line_dash="dash", line_color="#475569", line_width=2)
            fig_tat.update_layout(height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
            st.plotly_chart(fig_tat, width="stretch")

        with col_c3:
            st.markdown("<div style='min-height: 80px;'><h4 style='text-align: center; margin-bottom:0px; color: #475569;'>Active Login vs. Paid to Competitor<br><span style='font-size:14px; font-weight:normal;'><span style='color:#cbd5e1'>■</span> True Active Login &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#f97316'>■</span> Paid Competitor</span></h4></div>", unsafe_allow_html=True)
            paid_pcts = [f"({int((p/(a+p))*100)}%)" if (a+p)>0 else "(0%)" for a, p in zip(true_active_log, paid_comp_log)]
            fig_flight = go.Figure()
            fig_flight.add_trace(go.Bar(name="True Active Login", y=shared_y_branches, x=true_active_log, orientation='h', marker_color="#e2e8f0", text=[v if v>0 else "" for v in true_active_log], textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")))
            fig_flight.add_trace(go.Bar(name="Paid Competitor", y=shared_y_branches, x=paid_comp_log, orientation='h', marker_color="#f97316", text=[f"{v} {pct}" if v>0 else "" for v, pct in zip(paid_comp_log, paid_pcts)], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))
            fig_flight.update_layout(barmode="stack", height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"), showlegend=False)
            st.plotly_chart(fig_flight, width="stretch")

        st.divider()

        st.subheader("🔎 True Workable Login Leads Breakdown")
        col_w1, col_w2 = st.columns(2)
        with col_w1:
            st.markdown("<h4 style='text-align: center; color: #475569;'>Active Leads Aging</h4>", unsafe_allow_html=True)
            fig_log_aging = go.Figure()
            fig_log_aging.add_trace(go.Bar(name="< 7 Days", y=shared_y_branches, x=log_under_7, orientation='h', marker_color="#60a5fa", text=[f"{v}" if v > 0 else "" for v in log_under_7], textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold")))
            fig_log_aging.add_trace(go.Bar(name="> 7 Days", y=shared_y_branches, x=log_over_7, orientation='h', marker_color="#ef4444", text=[f"{v}" if v > 0 else "" for v in log_over_7], textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold")))
            fig_log_aging.update_layout(barmode="stack", height=380, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569")))
            st.plotly_chart(fig_log_aging, width="stretch")

        with col_w2:
            st.markdown("<h4 style='text-align: center; color: #475569;'>Competitor Pipeline Spread</h4>", unsafe_allow_html=True)
            fig_log_work = go.Figure()
            fig_log_work.add_trace(go.Bar(name="Exclusive (Safe)", y=shared_y_branches, x=log_exclusive, orientation='h', marker_color="#a7f3d0", text=[f"{v}" if v > 0 else "" for v in log_exclusive], textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold")))
            fig_log_work.add_trace(go.Bar(name="🚨 In Comp Sanction", y=shared_y_branches, x=log_comp_sanc, orientation='h', marker_color="#fda4af", text=[f"{v}" if v > 0 else "" for v in log_comp_sanc], textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold")))
            fig_log_work.update_layout(barmode="stack", height=380, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
            st.plotly_chart(fig_log_work, width="stretch")
        
        st.divider()

        # --- THE MISSING SECTION 3 CALCULATION ENGINE ---
        lost_log_df = log_df[log_df['lost_category'].astype(str).str.contains('Login', case=False, na=False)] if 'lost_category' in log_df.columns else pd.DataFrame()
        true_dead_lost, comp_san_lost, comp_pf_lost, log_leakage_pcts = [], [], [], []

        for b in shared_y_branches:
            total_shared_b = log_df[log_df['location'] == b].shape[0] if not log_df.empty else 0
            b_lost = lost_log_df[lost_log_df['location'] == b] if not lost_log_df.empty else pd.DataFrame()
            total_lost_b = b_lost.shape[0]

            log_leakage_pcts.append(round((total_lost_b / total_shared_b)*100, 1) if total_shared_b > 0 else 0)

            true_dead_lost.append(b_lost[b_lost['user_max_stage'] <= 2].shape[0] if not b_lost.empty else 0)
            comp_san_lost.append(b_lost[b_lost['user_max_stage'] == 3].shape[0] if not b_lost.empty else 0)
            comp_pf_lost.append(b_lost[b_lost['user_max_stage'] == 4].shape[0] if not b_lost.empty else 0)
        # -----------------------------------------------

        st.markdown('<div class="section-header"><h2>🚨 3. Login Stage Lost Analysis</h2></div>', unsafe_allow_html=True)
        col_l1, col_l2 = st.columns(2)

        with col_l1:
            st.markdown("<h4 style='text-align: center; color: #475569;'>Login Leakage Rate (% of Logins)<br><span style='font-size:13px; visibility:hidden;'>Invisible Spacer</span></h4>", unsafe_allow_html=True)
            leakage_colors = ["#9f1239" if p > 30 else ("#ef4444" if p > 20 else "#fca5a5") for p in log_leakage_pcts]
            fig_log_leakage = go.Figure(go.Bar(y=shared_y_branches, x=log_leakage_pcts, orientation='h', marker_color=leakage_colors, text=[f"{p}%" for p in log_leakage_pcts], textposition="inside", insidetextanchor="middle", textfont=dict(color=["white" if c in ["#9f1239", "#ef4444"] else "#0f172a" for c in leakage_colors], weight="bold")))
            fig_log_leakage.update_layout(height=350, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569")))
            st.plotly_chart(fig_log_leakage, width="stretch")

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
            st.plotly_chart(fig_log_lost_spread, width="stretch")

# ==========================================
# TAB 4: SANCTION TO PF DEEP DIVE
# ==========================================
with tab_san_pf:
    san_df = df_cohort[df_cohort['sanction_date'].notnull()] if 'sanction_date' in df_cohort.columns else pd.DataFrame()
    
    if not san_df.empty and 'location' in san_df.columns:
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

        st.markdown('<div class="section-header"><h2>🗂️ Sanction Distribution</h2></div>', unsafe_allow_html=True)
        card_cols = st.columns(6)
        for i, col in enumerate(card_cols):
            if i < len(top_branches):
                with col:
                    st.metric(label=f"📍 {top_branches[i]}", value=f"{san_vols[i]:,}", delta=f"{san_pcts[i]} Share", delta_color="off")
        st.divider()

        conv_rates, tat_days, true_active_san, paid_comp_san = [], [], [], []
        san_under_7, san_over_7 = [], []
        san_exclusive, san_comp_parallel = [], []

        active_san_df = san_df[san_df['lender_stage'] == 'Sanction'].copy() if 'lender_stage' in san_df.columns else pd.DataFrame()
        if not active_san_df.empty and 'sanction_date' in active_san_df.columns:
            active_san_df['aging_days'] = (pd.to_datetime('today') - active_san_df['sanction_date']).dt.days
        else:
            active_san_df['aging_days'] = 0

        for b in shared_y_branches:
            b_df = san_df[san_df['location'] == b]
            san_c = b_df.shape[0]
            pf_c = b_df['pf_date'].notnull().sum() if 'pf_date' in b_df.columns else 0
            
            conv_rates.append(round((pf_c/san_c)*100, 1) if san_c > 0 else 0)
            tat_days.append(round(b_df['tat_sanc_pf'].mean(), 1) if not b_df.empty and 'tat_sanc_pf' in b_df.columns and not pd.isna(b_df['tat_sanc_pf'].mean()) else 0)
            
            b_act = active_san_df[active_san_df['location'] == b] if 'location' in active_san_df.columns else pd.DataFrame()
            true_active_san.append(b_act[b_act['user_max_stage'] < 4].shape[0] if not b_act.empty else 0) 
            paid_comp_san.append(b_act[b_act['user_max_stage'] == 4].shape[0] if not b_act.empty else 0)  
            
            san_under_7.append(b_act[b_act['aging_days'] < 7].shape[0] if not b_act.empty else 0)
            san_over_7.append(b_act[b_act['aging_days'] >= 7].shape[0] if not b_act.empty else 0)
            
            san_exclusive.append(b_act[b_act['user_max_stage'] <= 3].shape[0] if not b_act.empty else 0)
            san_comp_parallel.append(0)

        st.markdown('<div class="section-header"><h2>📊 1. Conversion, Aging & Immediate Flight Risk</h2></div>', unsafe_allow_html=True)
        col_c1, col_c2, col_c3 = st.columns(3)
        
        with col_c1:
            tot_s = df_cohort['sanction_date'].notnull().sum() if 'sanction_date' in df_cohort.columns else 0
            tot_p = df_cohort['pf_date'].notnull().sum() if 'pf_date' in df_cohort.columns else 0
            nat_avg = round((tot_p / tot_s)*100, 1) if tot_s > 0 else 0
            
            st.markdown(f"<div style='min-height: 80px;'><h4 style='text-align: center; margin-bottom:0px; color: #475569;'>Sanction ➔ PF Rate<br><span style='font-size:14px; font-weight:normal;'>(Nat. Avg: {nat_avg}%)</span></h4></div>", unsafe_allow_html=True)
            conv_colors = ["#9f1239" if val < nat_avg else "#cbd5e1" for val in conv_rates]
            fig_conv = go.Figure(go.Bar(y=shared_y_branches, x=conv_rates, orientation='h', marker_color=conv_colors, text=[f"{v}%" for v in conv_rates], textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold")))
            fig_conv.add_vline(x=nat_avg, line_dash="dash", line_color="#475569", line_width=2)
            fig_conv.update_layout(height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569")))
            st.plotly_chart(fig_conv, width="stretch")

        with col_c2:
            target_tat = 5.0
            st.markdown(f"<div style='min-height: 80px;'><h4 style='text-align: center; margin-bottom:0px; color: #475569;'>Sanction ➔ PF TAT<br><span style='font-size:14px; font-weight:normal;'>(Target SLA: {target_tat} Days)</span></h4></div>", unsafe_allow_html=True)
            tat_colors = ["#9f1239" if val > target_tat else "#cbd5e1" for val in tat_days]
            fig_tat = go.Figure(go.Bar(y=shared_y_branches, x=tat_days, orientation='h', marker_color=tat_colors, text=[f"{v} days" for v in tat_days], textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold")))
            fig_tat.add_vline(x=target_tat, line_dash="dash", line_color="#475569", line_width=2)
            fig_tat.update_layout(height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
            st.plotly_chart(fig_tat, width="stretch")

        with col_c3:
            st.markdown("<div style='min-height: 80px;'><h4 style='text-align: center; margin-bottom:0px; color: #475569;'>Active Sanction vs. Paid to Competitor<br><span style='font-size:14px; font-weight:normal;'><span style='color:#cbd5e1'>■</span> True Active Sanction &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#f97316'>■</span> Paid Competitor</span></h4></div>", unsafe_allow_html=True)
            paid_pcts = [f"({int((p/(a+p))*100)}%)" if (a+p)>0 else "(0%)" for a, p in zip(true_active_san, paid_comp_san)]
            fig_flight = go.Figure()
            fig_flight.add_trace(go.Bar(name="True Active Sanction", y=shared_y_branches, x=true_active_san, orientation='h', marker_color="#e2e8f0", text=[v if v>0 else "" for v in true_active_san], textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")))
            fig_flight.add_trace(go.Bar(name="Paid Competitor", y=shared_y_branches, x=paid_comp_san, orientation='h', marker_color="#f97316", text=[f"{v} {pct}" if v>0 else "" for v, pct in zip(paid_comp_san, paid_pcts)], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))
            fig_flight.update_layout(barmode="stack", height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"), showlegend=False)
            st.plotly_chart(fig_flight, width="stretch")

        st.divider()

        st.subheader("🔎 True Workable Sanction Leads Breakdown")
        col_w1, col_w2 = st.columns(2)
        with col_w1:
            st.markdown("<h4 style='text-align: center; color: #475569;'>Active Leads Aging</h4>", unsafe_allow_html=True)
            fig_san_aging = go.Figure()
            fig_san_aging.add_trace(go.Bar(name="< 7 Days", y=shared_y_branches, x=san_under_7, orientation='h', marker_color="#60a5fa", text=[f"{v}" if v > 0 else "" for v in san_under_7], textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold")))
            fig_san_aging.add_trace(go.Bar(name="> 7 Days", y=shared_y_branches, x=san_over_7, orientation='h', marker_color="#ef4444", text=[f"{v}" if v > 0 else "" for v in san_over_7], textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold")))
            fig_san_aging.update_layout(barmode="stack", height=380, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569")))
            st.plotly_chart(fig_san_aging, width="stretch")

        with col_w2:
            st.markdown("<h4 style='text-align: center; color: #475569;'>Competitor Pipeline Spread</h4>", unsafe_allow_html=True)
            fig_san_work = go.Figure()
            fig_san_work.add_trace(go.Bar(name="Exclusive (Safe)", y=shared_y_branches, x=san_exclusive, orientation='h', marker_color="#a7f3d0", text=[f"{v}" if v > 0 else "" for v in san_exclusive], textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold")))
            fig_san_work.add_trace(go.Bar(name="🚨 Parallel Comp Sanction", y=shared_y_branches, x=san_comp_parallel, orientation='h', marker_color="#fda4af", text=[f"{v}" if v > 0 else "" for v in san_comp_parallel], textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold")))
            fig_san_work.update_layout(barmode="stack", height=380, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
            st.plotly_chart(fig_san_work, width="stretch")
        
        st.divider()

        # --- THE MISSING SECTION 3 CALCULATION ENGINE ---
        lost_san_df = san_df[san_df['lost_category'].astype(str).str.contains('Sanction', case=False, na=False)] if 'lost_category' in san_df.columns else pd.DataFrame()
        true_dead_lost, comp_pf_lost, san_leakage_pcts = [], [], []

        for b in shared_y_branches:
            total_shared_b = san_df[san_df['location'] == b].shape[0] if not san_df.empty else 0
            b_lost = lost_san_df[lost_san_df['location'] == b] if not lost_san_df.empty else pd.DataFrame()
            total_lost_b = b_lost.shape[0]

            san_leakage_pcts.append(round((total_lost_b / total_shared_b)*100, 1) if total_shared_b > 0 else 0)

            true_dead_lost.append(b_lost[b_lost['user_max_stage'] <= 3].shape[0] if not b_lost.empty else 0)
            comp_pf_lost.append(b_lost[b_lost['user_max_stage'] == 4].shape[0] if not b_lost.empty else 0)
        # -----------------------------------------------

        st.markdown('<div class="section-header"><h2>🚨 3. Sanction Stage Lost Analysis</h2></div>', unsafe_allow_html=True)
        col_l1, col_l2 = st.columns(2)

        with col_l1:
            st.markdown("<h4 style='text-align: center; color: #475569;'>Sanction Leakage Rate (% of Sanctions)<br><span style='font-size:13px; visibility:hidden;'>Invisible Spacer</span></h4>", unsafe_allow_html=True)
            leakage_colors = ["#9f1239" if p > 15 else ("#ef4444" if p > 5 else "#fca5a5") for p in san_leakage_pcts]
            fig_san_leakage = go.Figure(go.Bar(y=shared_y_branches, x=san_leakage_pcts, orientation='h', marker_color=leakage_colors, text=[f"{p}%" if p > 0 else "0%" for p in san_leakage_pcts], textposition="inside", insidetextanchor="middle", textfont=dict(color=["white" if c in ["#9f1239", "#ef4444"] else "#0f172a" for c in leakage_colors], weight="bold")))
            fig_san_leakage.update_layout(height=350, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569")))
            st.plotly_chart(fig_san_leakage, width="stretch")

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
            st.plotly_chart(fig_san_lost_spread, width="stretch")
