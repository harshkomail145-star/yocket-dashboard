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
        fig_top_metrics.add_trace(go.Bar(name="Fall '25", x=stages, y=fall_25_data, marker_color=COLOR_FALL_25, text=fall_25_data, textposition='outside', textfont=dict(size=14, color='black')))
        fig_top_metrics.add_trace(go.Bar(name="Fall '26", x=stages, y=fall_26_data, marker_color=COLOR_FALL_26, text=fall_26_data, textposition='outside', textfont=dict(size=14, color='black')))

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
        fig_yoy_bar.add_trace(go.Bar(name="Fall '25", x=months_list, y=fall_25_logins, marker_color=COLOR_FALL_25, text=fall_25_logins, textposition='outside', textfont=dict(size=14, color='black')))
        fig_yoy_bar.add_trace(go.Bar(name="Fall '26", x=months_list, y=fall_26_logins, marker_color=COLOR_FALL_26, text=fall_26_logins, textposition='outside', textfont=dict(size=14, color='black')))

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
    
    # --- DYNAMIC X-AXIS LABELS (Active/Lost at the bottom) ---
    dynamic_stages = []
    for i, stage_name in enumerate(stages):
        if i < 3: # Shared, Login, Sanction
            # Injects the Lost and Active numbers directly under the stage name on the X-axis
            label = f"<b>{stage_name}</b><br><span style='font-size: 13px;'><b style='color: #ef4444;'>{losts[i]:,} Lost</b> &nbsp;|&nbsp; <b style='color: #16a34a;'>{currents[i]:,} Active</b></span>"
        else: # PF Paid (No active/lost needed)
            label = f"<b>{stage_name}</b>"
        dynamic_stages.append(label)

    # --- DYNAMIC TEXT POSITIONING (For the big numbers only) ---
    max_vol = max(totals) if totals else 1
    # If the bar is super thin (< 25%), pop the big number outside
    dynamic_positions = ["outside" if v < (max_vol * 0.25) else "inside" for v in totals]
    
    custom_text = []
    for tot, pos in zip(totals, dynamic_positions):
        main_col = '#1e293b' if pos == 'outside' else 'white'
        # Only the big number goes inside the bar now! Much cleaner.
        txt = f"<b style='font-size: 32px; color: {main_col};'>{tot:,}</b>"
        custom_text.append(txt)
    
    fig_funnel = go.Figure(go.Funnel(
        orientation='v', 
        x=dynamic_stages, # Using the new dynamic labels here
        y=totals, 
        text=custom_text, 
        textposition=dynamic_positions, 
        textinfo="text",
        marker={"color": ["#4f46e5", "#6366f1", "#818cf8", "#a5b4fc"], "line": {"width": [2, 2, 2, 2], "color": ["white"]*4}},
        connector={"line": {"color": "#e2e8f0", "dash": "solid", "width": 2}, "fillcolor": "rgba(226, 232, 240, 0.4)"}
    ))
    
    # Safely apply cliponaxis so popped-out text is never cut off
    fig_funnel.update_traces(cliponaxis=False)
    
    bp_log_pct = (tot_login/tot_shared)*100 if tot_shared > 0 else 0
    log_san_pct = (tot_sanc/tot_login)*100 if tot_login > 0 else 0
    san_pf_pct = (tot_pf/tot_sanc)*100 if tot_sanc > 0 else 0
    
    fig_funnel.add_annotation(x=0.5, y=1.05, xref="x", yref="paper", text=f"<b>{bp_log_pct:.1f}% ➔</b>", showarrow=False, font=dict(size=14, color="#4f46e5"), bgcolor="#ffffff", bordercolor="#e2e8f0", borderwidth=1, borderpad=5)
    fig_funnel.add_annotation(x=1.5, y=1.05, xref="x", yref="paper", text=f"<b>{log_san_pct:.1f}% ➔</b>", showarrow=False, font=dict(size=14, color="#4f46e5"), bgcolor="#ffffff", bordercolor="#e2e8f0", borderwidth=1, borderpad=5)
    fig_funnel.add_annotation(x=2.5, y=1.05, xref="x", yref="paper", text=f"<b>{san_pf_pct:.1f}% ➔</b>", showarrow=False, font=dict(size=14, color="#4f46e5"), bgcolor="#ffffff", bordercolor="#e2e8f0", borderwidth=1, borderpad=5)
    
    max_funnel_range = max(totals) * 0.6 if totals else 1600
    
    # Bumped bottom margin ('b': 80) to give the new X-axis labels room to breathe
    fig_funnel.update_layout(
        height=400, 
        margin={"t": 120, "b": 80, "l": 20, "r": 100}, 
        plot_bgcolor='rgba(0,0,0,0)', 
        paper_bgcolor='rgba(0,0,0,0)', 
        xaxis=dict(showline=False, tickfont=dict(size=15, weight="normal", color="#1e293b")), 
        yaxis=dict(showticklabels=False, showgrid=False, range=[-max_funnel_range, max_funnel_range])
    )
    
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

    # 1. Safely extract potential losses (Flight Risk)
    bp_pot = lost_bp_df[lost_bp_df['user_max_stage'] > 1].copy() if not lost_bp_df.empty else pd.DataFrame()
    log_pot = lost_log_df[lost_log_df['user_max_stage'] > 2].copy() if not lost_log_df.empty else pd.DataFrame()
    san_pot = lost_san_df[lost_san_df['user_max_stage'] > 3].copy() if not lost_san_df.empty else pd.DataFrame()

    # 2. Combine them safely to find the true Top 5 reasons across the entire pipeline
    valid_dfs = [df for df in [bp_pot, log_pot, san_pot] if not df.empty and 'lost_reason' in df.columns]
    all_pot = pd.concat(valid_dfs) if valid_dfs else pd.DataFrame()
    
    if all_pot.empty or 'lost_reason' not in all_pot.columns:
        st.info("No flight risk leads found with recorded reasons for this selection.")
    else:
        top_reasons = all_pot['lost_reason'].value_counts().head(5).index.tolist()
        
        stages_data = [
            ("Lost from Sanction", san_pot),
            ("Lost from Login", log_pot),
            ("Lost from BP", bp_pot)
        ]
        
        y_labels = []
        reason_data = {r: [] for r in top_reasons}
        reason_data["Other"] = []
        stage_totals = []

        # 3. Aggregate data for the 3 horizontal bars
        for stage_name, df_pot in stages_data:
            tot = df_pot.shape[0] if not df_pot.empty else 0
            stage_totals.append(tot)
            y_labels.append(f"<b>{stage_name}</b><br>{tot} Flight Risk")
            
            if tot > 0 and 'lost_reason' in df_pot.columns:
                for r in top_reasons:
                    reason_data[r].append(df_pot[df_pot['lost_reason'] == r].shape[0])
                other_c = df_pot[~df_pot['lost_reason'].isin(top_reasons)].shape[0]
                reason_data["Other"].append(other_c)
            else:
                for r in top_reasons:
                    reason_data[r].append(0)
                reason_data["Other"].append(0)

        fig_reasons = go.Figure()
        # Distinct, professional color palette for the 5 reasons + 'Other'
        reason_colors = ["#3b82f6", "#8b5cf6", "#f59e0b", "#10b981", "#ef4444", "#94a3b8"]

        # 4. Build the 100% Stacked Bars dynamically
        for idx, r in enumerate(top_reasons + ["Other"]):
            raw_vals = reason_data[r]
            
            # Using 0 instead of None to prevent the Plotly blank chart bug you saw earlier
            pct_vals = [(v/t)*100 if t > 0 else 0 for v, t in zip(raw_vals, stage_totals)]
            labels = [f"{p:.0f}%" if p > 0 else "" for p in pct_vals]
            
            # Only draw the trace if this reason actually occurred
            if sum(raw_vals) > 0: 
                fig_reasons.add_trace(go.Bar(
                    name=r, 
                    y=y_labels, 
                    x=pct_vals, 
                    orientation='h', 
                    marker_color=reason_colors[idx % len(reason_colors)], 
                    text=labels, 
                    textposition="inside", 
                    insidetextanchor="middle", 
                    textfont=dict(color="white", weight="bold")
                ))

        # 5. Render layout with dynamic top legend
        fig_reasons.update_layout(
            barmode="stack", 
            height=340, 
            margin=dict(t=40, b=20, l=20, r=20), 
            plot_bgcolor="rgba(0,0,0,0)", 
            paper_bgcolor="rgba(0,0,0,0)", 
            legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), 
            xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]), 
            yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b")) 
        )
        st.plotly_chart(fig_reasons, width="stretch")
        
    # --- SECTION 8: REGION-WISE COHORT FUNNEL GRAPHIC ---
    st.divider()
    st.markdown('<div class="section-header"><h2>🌍 8. Region-Wise Cohort Funnel Graphic</h2></div>', unsafe_allow_html=True)
    st.markdown("A purely graphical matrix. Each column compares branch performance at a specific stage, while the text on the bars reveals the exact volume and stage-to-stage conversion percentage.")

    region_df = df_cohort[df_cohort['date_shared'].notnull()].copy() if 'date_shared' in df_cohort.columns else pd.DataFrame()

    if region_df.empty or 'location' not in region_df.columns:
        st.info("No location data available for region-wise analysis.")
    else:
        # 1. Aggregate funnel data by location
        grp = region_df.groupby('location').agg(
            Shared=('date_shared', 'count'),
            Login=('login_date', 'count'),
            Sanction=('sanction_date', 'count'),
            PF=('pf_date', 'count')
        ).reset_index()

        # Sort by Shared volume and limit to Top 10 to keep the graphic clean
        grp = grp.sort_values('Shared', ascending=False).head(10)
        
        # Calculate exact drop-off percentages safely
        grp['l_pct'] = (grp['Login'] / grp['Shared'] * 100).fillna(0)
        grp['s_pct'] = (grp['Sanction'] / grp['Login'] * 100).fillna(0)
        grp['p_pct'] = (grp['PF'] / grp['Sanction'] * 100).fillna(0)

        # Reverse for Plotly top-down rendering
        grp = grp.iloc[::-1]
        y_labels = grp['location']

        fig_matrix = go.Figure()

        # Stage 1: Shared
        fig_matrix.add_trace(go.Bar(
            y=y_labels, x=grp['Shared'], orientation='h',
            marker_color="#cbd5e1", # Neutral Gray for base
            text=[f"<b>{int(v)}</b>" if v > 0 else "" for v in grp['Shared']],
            textposition="auto", name="Shared", hoverinfo="skip"
        ))

        # Stage 2: Login
        fig_matrix.add_trace(go.Bar(
            y=y_labels, x=grp['Login'], orientation='h', xaxis='x2',
            marker_color="#93c5fd", # Light Blue
            text=[f"<b>{int(v)}</b> ({p:.0f}%)" if v > 0 else "" for v, p in zip(grp['Login'], grp['l_pct'])],
            textposition="auto", name="Login", hoverinfo="skip"
        ))

        # Stage 3: Sanction
        fig_matrix.add_trace(go.Bar(
            y=y_labels, x=grp['Sanction'], orientation='h', xaxis='x3',
            marker_color="#3b82f6", # Solid Blue
            text=[f"<b>{int(v)}</b> ({p:.0f}%)" if v > 0 else "" for v, p in zip(grp['Sanction'], grp['s_pct'])],
            textposition="auto", name="Sanction", hoverinfo="skip"
        ))

        # Stage 4: PF Paid
        fig_matrix.add_trace(go.Bar(
            y=y_labels, x=grp['PF'], orientation='h', xaxis='x4',
            marker_color="#10b981", # Emerald Green for terminal success
            text=[f"<b>{int(v)}</b> ({p:.0f}%)" if v > 0 else "" for v, p in zip(grp['PF'], grp['p_pct'])],
            textposition="auto", name="PF", hoverinfo="skip"
        ))

        # Build the 4-column sub-axis layout dynamically
        fig_matrix.update_layout(
            height=200 + (len(grp) * 40), # Scales height dynamically based on branch count
            margin=dict(t=60, b=20, l=10, r=20),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            # The domain maps out 4 evenly spaced horizontal zones for the columns
            xaxis=dict(domain=[0, 0.22], showgrid=False, showticklabels=False, title="<b>1. Shared Vol</b>"),
            xaxis2=dict(domain=[0.26, 0.48], showgrid=False, showticklabels=False, title="<b>2. Login (% of BP)</b>"),
            xaxis3=dict(domain=[0.52, 0.74], showgrid=False, showticklabels=False, title="<b>3. Sanc (% of Log)</b>"),
            xaxis4=dict(domain=[0.78, 1.0], showgrid=False, showticklabels=False, title="<b>4. PF (% of Sanc)</b>"),
            yaxis=dict(tickfont=dict(size=13, weight="bold", color="#1e293b"))
        )
        
        st.plotly_chart(fig_matrix, width="stretch")
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
        # --- ROW 4: QUERY RESOLUTION STATUS (WORKABLE BP LEADS) ---
        st.markdown('<div class="section-header"><h2>❓ 4. Query Resolution Status (Workable BP Leads)</h2></div>', unsafe_allow_html=True)
        st.markdown("Tracking resolved vs. unresolved queries specifically for **Active Workable** BP leads. (Excludes leads without queries).")

        res_vals = []
        unres_vals = []
        query_totals = []
        branch_query_labels = []

        for b in shared_y_branches:
            # 1. Get active leads for this branch
            b_act = active_bp_df[active_bp_df['location'] == b] if not active_bp_df.empty else pd.DataFrame()
            
            # 2. Filter to WORKABLE leads (exclude Terminal Loss / Stage 4)
            b_workable = b_act[b_act['user_max_stage'] < 4] if not b_act.empty else pd.DataFrame()
            
            # 3. Filter to ONLY leads that actually have a query (safeguarded in case columns are missing)
            if not b_workable.empty and 'latest_query' in b_workable.columns and 'query_status' in b_workable.columns:
                # Ensure latest_query is not null and not empty whitespace
                b_queried = b_workable[b_workable['latest_query'].notna() & (b_workable['latest_query'].astype(str).str.strip() != "")]
                
                total_q = b_queried.shape[0]
                # Using lower() and strip() makes it immune to accidental spaces or capitalization in the CSV
                resolved_c = b_queried[b_queried['query_status'].astype(str).str.strip().str.lower() == 'resolved'].shape[0]
                unresolved_c = b_queried[b_queried['query_status'].astype(str).str.strip().str.lower() == 'unresolved'].shape[0]
            else:
                total_q, resolved_c, unresolved_c = 0, 0, 0
                
            query_totals.append(total_q)
            res_vals.append(resolved_c)
            unres_vals.append(unresolved_c)
            
            # Update Y-Axis labels to show the specific query count
            branch_query_labels.append(f"<b>{b}</b><br>{total_q} Queries")

        # Convert to 100% scale
        res_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(res_vals, query_totals)]
        unres_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(unres_vals, query_totals)]

        # Format labels for inside the bars
        res_labels = [f"{p:.0f}%" if p > 0 else "" for p in res_pct_num]
        unres_labels = [f"{p:.0f}%" if p > 0 else "" for p in unres_pct_num]

        fig_query_bp = go.Figure()
        fig_query_bp.add_trace(go.Bar(name="✅ Resolved", y=branch_query_labels, x=res_pct_num, orientation='h', marker_color="#a7f3d0", text=res_labels, textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="#0f172a")))
        fig_query_bp.add_trace(go.Bar(name="⏳ Unresolved", y=branch_query_labels, x=unres_pct_num, orientation='h', marker_color="#fca5a5", text=unres_labels, textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="#9f1239")))

        # Lock X-axis to 100 for the stacked percentage layout
        fig_query_bp.update_layout(barmode="stack", height=350, margin=dict(t=40, b=20, l=20, r=20), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]), yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b"), autorange="reversed"))
        
        st.plotly_chart(fig_query_bp, width="stretch")
        st.divider()
        # --- ROW 5: LOST POTENTIAL ANALYSIS (BRANCH-WISE 100% STACKED) ---
        st.markdown('<div class="section-header"><h2>🚨 5. Lost Potential Analysis (Branch-wise)</h2></div>', unsafe_allow_html=True)
        st.markdown("Out of the total files formally lost from BP, this tracks how many went to a competitor and **exactly what stage the competitor reached with them**.")

        true_dead_vals = []
        comp_log_vals = []
        comp_san_vals = []
        comp_pf_vals = []
        lost_branch_totals = []
        branch_lost_labels = []
        potential_loss_pcts = []

        for b in shared_y_branches:
            # 1. Isolate the formally lost BP leads for this branch
            b_lost = lost_bp_df[lost_bp_df['location'] == b] if not lost_bp_df.empty else pd.DataFrame()
            tot_lost = b_lost.shape[0]
            
            # 2. Break down their furthest reached stage
            td = b_lost[b_lost['user_max_stage'] <= 1].shape[0] if not b_lost.empty else 0
            clog = b_lost[b_lost['user_max_stage'] == 2].shape[0] if not b_lost.empty else 0
            csan = b_lost[b_lost['user_max_stage'] == 3].shape[0] if not b_lost.empty else 0
            cpf = b_lost[b_lost['user_max_stage'] == 4].shape[0] if not b_lost.empty else 0
            
            lost_branch_totals.append(tot_lost)
            true_dead_vals.append(td)
            comp_log_vals.append(clog)
            comp_san_vals.append(csan)
            comp_pf_vals.append(cpf)
            
            # 3. Format Y-Axis with the specific count of lost leads
            branch_lost_labels.append(f"<b>{b}</b><br>{tot_lost} Lost Leads")
            
            # Calculate the total % of lost leads that went to a competitor
            potential_loss_pcts.append(f"{((tot_lost - td) / tot_lost) * 100:.1f}%" if tot_lost > 0 else "0%")

        # Convert raw counts to 100% scale
        td_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(true_dead_vals, lost_branch_totals)]
        cl_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(comp_log_vals, lost_branch_totals)]
        cs_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(comp_san_vals, lost_branch_totals)]
        cp_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(comp_pf_vals, lost_branch_totals)]

        td_labels = [f"{p:.0f}%" if p > 0 else "" for p in td_pct_num]
        cl_labels = [f"{p:.0f}%" if p > 0 else "" for p in cl_pct_num]
        cs_labels = [f"{p:.0f}%" if p > 0 else "" for p in cs_pct_num]
        cp_labels = [f"{p:.0f}%" if p > 0 else "" for p in cp_pct_num]

        fig_lost_bp = go.Figure()
        fig_lost_bp.add_trace(go.Bar(name="True Dead", y=branch_lost_labels, x=td_pct_num, orientation='h', marker_color="#e2e8f0", text=td_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")))
        fig_lost_bp.add_trace(go.Bar(name="In Comp Login", y=branch_lost_labels, x=cl_pct_num, orientation='h', marker_color="#fdba74", text=cl_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="#9a3412", weight="bold")))
        fig_lost_bp.add_trace(go.Bar(name="In Comp Sanction", y=branch_lost_labels, x=cs_pct_num, orientation='h', marker_color="#f97316", text=cs_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))
        fig_lost_bp.add_trace(go.Bar(name="Comp PF Paid", y=branch_lost_labels, x=cp_pct_num, orientation='h', marker_color="#9f1239", text=cp_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))

        # Append the Lost Potential Warning to the end of the bars
        for i, b in enumerate(branch_lost_labels):
            if lost_branch_totals[i] > 0:
                fig_lost_bp.add_annotation(x=100, y=b, text=f"<span style='color:#64748b; font-size:11px; font-weight:normal;'>Lost Potential</span><br><b style='font-size:16px; color:#9f1239;'>⚠️ {potential_loss_pcts[i]}</b>", showarrow=False, xanchor="left", xshift=15, align="left")

        # Range extended to 125 to fit the right-side text annotations
        fig_lost_bp.update_layout(barmode="stack", height=380, margin=dict(t=40, b=20, l=20, r=100), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False, range=[0, 125]), yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b"), autorange="reversed"))
        st.plotly_chart(fig_lost_bp, width="stretch")
        # --- ROW 6: FLIGHT RISK AUTOPSY (BRANCH-WISE REASONS) ---
        st.markdown('<div class="section-header"><h2>🕵️ 6. Flight Risk Autopsy (Why Did We Lose Them?)</h2></div>', unsafe_allow_html=True)
        st.markdown("For the leads that **progressed with a competitor** (Potential Loss), this shows the exact reasons they were tagged as lost by our team.")

        # 1. Filter strictly to leads lost from BP that progressed to Login/Sanction/PF elsewhere
        bp_flight_risk_df = lost_bp_df[lost_bp_df['user_max_stage'] > 1].copy() if not lost_bp_df.empty else pd.DataFrame()

        if bp_flight_risk_df.empty or 'lost_reason' not in bp_flight_risk_df.columns:
            st.info("No flight risk leads found with recorded reasons for this selection.")
        else:
            # 2. Get the Top 4 reasons overall to keep the stacked bar clean and readable
            top_reasons = bp_flight_risk_df['lost_reason'].value_counts().head(4).index.tolist()
            
            branch_reason_labels = []
            reason_data = {r: [] for r in top_reasons}
            reason_data["Other"] = []
            branch_fr_totals = []

            for b in shared_y_branches:
                b_fr = bp_flight_risk_df[bp_flight_risk_df['location'] == b]
                tot_fr = b_fr.shape[0]
                
                branch_fr_totals.append(tot_fr)
                branch_reason_labels.append(f"<b>{b}</b><br>{tot_fr} Flight Risk")
                
                if tot_fr > 0:
                    for r in top_reasons:
                        reason_data[r].append(b_fr[b_fr['lost_reason'] == r].shape[0])
                    # Group any remaining rare reasons into "Other"
                    other_count = b_fr[~b_fr['lost_reason'].isin(top_reasons)].shape[0]
                    reason_data["Other"].append(other_count)
                else:
                    for r in top_reasons:
                        reason_data[r].append(0)
                    reason_data["Other"].append(0)
            
            fig_reasons_bp = go.Figure()
            # Professional color palette for the different reasons
            reason_colors = ["#3b82f6", "#8b5cf6", "#f59e0b", "#10b981", "#94a3b8"] 
            
            # 3. Build the 100% Stacked Bars dynamically
            for idx, r in enumerate(top_reasons + ["Other"]):
                raw_vals = reason_data[r]
                
                # Convert to percentages
                pct_vals = [(v/t)*100 if t > 0 else 0 for v, t in zip(raw_vals, branch_fr_totals)]
                labels = [f"{p:.0f}%" if p > 0 else "" for p in pct_vals]
                
                # Only draw the segment if this reason actually exists in the current view
                if sum(raw_vals) > 0:
                    fig_reasons_bp.add_trace(go.Bar(
                        name=r, 
                        y=branch_reason_labels, 
                        x=pct_vals, 
                        orientation='h', 
                        marker_color=reason_colors[idx % len(reason_colors)], 
                        text=labels, 
                        textposition="inside", 
                        insidetextanchor="middle", 
                        textfont=dict(color="white", weight="bold")
                    ))
            
            fig_reasons_bp.update_layout(
                barmode="stack", 
                height=380, 
                margin=dict(t=40, b=20, l=20, r=20), 
                plot_bgcolor="rgba(0,0,0,0)", 
                paper_bgcolor="rgba(0,0,0,0)", 
                legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), 
                xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]), 
                yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b"), autorange="reversed")
            )
            st.plotly_chart(fig_reasons_bp, width="stretch")
            
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
        log_y_branches = [b for b in top_branches if b != "Others"]

        st.markdown('<div class="section-header"><h2>🗂️ Login Stage Lead Distribution</h2></div>', unsafe_allow_html=True)
        card_cols = st.columns(6)
        for i, col in enumerate(card_cols):
            if i < len(top_branches):
                with col:
                    st.metric(label=f"📍 {top_branches[i]}", value=f"{log_vols[i]:,}", delta=f"{log_pcts[i]} Share", delta_color="off")
        st.divider()

        # --- DATA ENGINE FOR TAB 3 ---
        conv_rates, tat_days = [], []
        active_log_counts, lost_log_counts = [], []
        log_u7_vals, log_o7_vals, log_term_vals = [], [], []

        active_log_df = log_df[log_df['lender_stage'] == 'Login'].copy() if 'lender_stage' in log_df.columns else pd.DataFrame()
        if not active_log_df.empty and 'login_date' in active_log_df.columns:
            active_log_df['aging_days'] = (pd.to_datetime('today') - active_log_df['login_date']).dt.days
        else:
            active_log_df['aging_days'] = 0
            
        lost_log_df = log_df[log_df['lost_category'].astype(str).str.contains('Login', case=False, na=False)] if 'lost_category' in log_df.columns else pd.DataFrame()

        for b in log_y_branches:
            b_df = log_df[log_df['location'] == b]
            log_c = b_df.shape[0]
            san_c = b_df['sanction_date'].notnull().sum() if 'sanction_date' in b_df.columns else 0
            
            conv_rates.append(round((san_c/log_c)*100, 1) if log_c > 0 else 0)
            tat_days.append(round(b_df['tat_login_sanc'].mean(), 1) if not b_df.empty and 'tat_login_sanc' in b_df.columns and not pd.isna(b_df['tat_login_sanc'].mean()) else 0)
            
            b_act = active_log_df[active_log_df['location'] == b] if not active_log_df.empty else pd.DataFrame()
            b_lost = lost_log_df[lost_log_df['location'] == b] if not lost_log_df.empty else pd.DataFrame()
            
            active_log_counts.append(b_act.shape[0])
            lost_log_counts.append(b_lost.shape[0])
            
            u7 = b_act[(b_act['aging_days'] < 7) & (b_act['user_max_stage'] < 4)].shape[0] if not b_act.empty else 0
            o7 = b_act[(b_act['aging_days'] >= 7) & (b_act['user_max_stage'] < 4)].shape[0] if not b_act.empty else 0
            term = b_act[b_act['user_max_stage'] == 4].shape[0] if not b_act.empty else 0
            
            log_u7_vals.append(u7)
            log_o7_vals.append(o7)
            log_term_vals.append(term)

        # --- ROW 1: CONVERSION, TAT & VOLUMES (4-COLUMN GRID) ---
        st.markdown('<div class="section-header"><h2>📊 1. Branch Performance Matrix</h2></div>', unsafe_allow_html=True)
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        
        with col_c1:
            tot_s = log_df.shape[0] if not log_df.empty else 0
            tot_l = log_df['sanction_date'].notnull().sum() if not log_df.empty and 'sanction_date' in log_df.columns else 0
            lender_avg_conv = round((tot_l / tot_s)*100, 1) if tot_s > 0 else 0
            
            st.markdown(f"<div style='min-height: 80px;'><h4 style='text-align: center; margin-bottom:0px; color: #475569;'>Login ➔ Sanction Rate<br><span style='font-size:14px; font-weight:normal;'>(Lender Avg: {lender_avg_conv}%)</span></h4></div>", unsafe_allow_html=True)
            conv_colors = ["#9f1239" if val < lender_avg_conv else "#cbd5e1" for val in conv_rates]
            fig_conv = go.Figure(go.Bar(y=log_y_branches, x=conv_rates, orientation='h', marker_color=conv_colors, text=[f"{v}%" for v in conv_rates], textposition="inside", insidetextanchor="middle", textfont=dict(color=["white" if c == "#9f1239" else "#0f172a" for c in conv_colors], weight="bold")))
            fig_conv.add_vline(x=lender_avg_conv, line_dash="dash", line_color="#475569", line_width=2)
            fig_conv.update_layout(height=320, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569")))
            st.plotly_chart(fig_conv, width="stretch")

        with col_c2:
            lender_avg_tat = round(log_df['tat_login_sanc'].mean(), 1) if not log_df.empty and 'tat_login_sanc' in log_df.columns and not pd.isna(log_df['tat_login_sanc'].mean()) else 0
            
            st.markdown(f"<div style='min-height: 80px;'><h4 style='text-align: center; margin-bottom:0px; color: #475569;'>Login ➔ Sanction TAT<br><span style='font-size:14px; font-weight:normal;'>(Lender Avg: {lender_avg_tat} Days)</span></h4></div>", unsafe_allow_html=True)
            tat_colors = ["#9f1239" if val > lender_avg_tat else "#cbd5e1" for val in tat_days]
            fig_tat = go.Figure(go.Bar(y=log_y_branches, x=tat_days, orientation='h', marker_color=tat_colors, text=[f"{v} days" for v in tat_days], textposition="inside", insidetextanchor="middle", textfont=dict(color=["white" if c == "#9f1239" else "#0f172a" for c in tat_colors], weight="bold")))
            fig_tat.add_vline(x=lender_avg_tat, line_dash="dash", line_color="#475569", line_width=2)
            fig_tat.update_layout(height=320, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
            st.plotly_chart(fig_tat, width="stretch")

        with col_c3:
            st.markdown("<div style='min-height: 80px;'><h4 style='text-align: center; margin-bottom:0px; color: #475569;'>Current Active Leads<br><span style='font-size:14px; font-weight:normal;'>(Sitting in Login Stage)</span></h4></div>", unsafe_allow_html=True)
            fig_act = go.Figure(go.Bar(y=log_y_branches, x=active_log_counts, orientation='h', marker_color="#3b82f6", text=[f"{v}" for v in active_log_counts], textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="white")))
            fig_act.update_layout(height=320, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
            st.plotly_chart(fig_act, width="stretch")

        with col_c4:
            st.markdown("<div style='min-height: 80px;'><h4 style='text-align: center; margin-bottom:0px; color: #475569;'>Total Lost Leads<br><span style='font-size:14px; font-weight:normal;'>(Lost from Login Stage)</span></h4></div>", unsafe_allow_html=True)
            fig_lst = go.Figure(go.Bar(y=log_y_branches, x=lost_log_counts, orientation='h', marker_color="#ef4444", text=[f"{v}" for v in lost_log_counts], textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="white")))
            fig_lst.update_layout(height=320, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
            st.plotly_chart(fig_lst, width="stretch")

        st.divider()

        # --- ROW 2: ACTIVE PIPELINE HEALTH ---
        st.markdown('<div class="section-header"><h2>⏱️ 2. Active Pipeline Health (Branch-wise)</h2></div>', unsafe_allow_html=True)
        st.markdown("A macro view of your **Active Login** pipeline. Breaking down healthy leads vs. aging bottlenecks vs. terminal competitor leakage.")

        totals_health_log = [u + o + c for u, o, c in zip(log_u7_vals, log_o7_vals, log_term_vals)]
        branch_health_labels = [f"<b>{b}</b><br>{t} Active" for b, t in zip(log_y_branches, totals_health_log)]

        u7_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(log_u7_vals, totals_health_log)]
        o7_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(log_o7_vals, totals_health_log)]
        term_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(log_term_vals, totals_health_log)]

        u7_labels = [f"{p:.0f}%" if p > 0 else "" for p in u7_pct_num]
        o7_labels = [f"{p:.0f}%" if p > 0 else "" for p in o7_pct_num]
        term_labels = [f"{p:.0f}%" if p > 0 else "" for p in term_pct_num]

        fig_health_log = go.Figure()
        fig_health_log.add_trace(go.Bar(name="< 7 Days (Active)", y=branch_health_labels, x=u7_pct_num, orientation='h', marker_color="#a7f3d0", text=u7_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="#0f172a", weight="bold")))
        fig_health_log.add_trace(go.Bar(name="> 7 Days (Aging)", y=branch_health_labels, x=o7_pct_num, orientation='h', marker_color="#fed7aa", text=o7_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="#0f172a", weight="bold")))
        fig_health_log.add_trace(go.Bar(name="Terminal Loss to Competitor", y=branch_health_labels, x=term_pct_num, orientation='h', marker_color="#9f1239", text=term_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))

        fig_health_log.update_layout(barmode="stack", height=380, margin=dict(t=40, b=20, l=20, r=20), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]), yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b"), autorange="reversed"))
        st.plotly_chart(fig_health_log, width="stretch")
        
        st.divider()

        # --- ROW 3: LOSING THE ACTIVE PROSPECTS ---
        st.markdown('<div class="section-header"><h2>💸 3. Losing The Active Prospects (Branch-wise)</h2></div>', unsafe_allow_html=True)
        st.markdown("Where our **Workable** Login leads are sitting. *(Note: Active Login leads cannot be 'In Comp Login', so flight risk only triggers if they reach Competitor Sanction)*.")

        log_exc_vals, log_csan_vals, log_workable_totals = [], [], []

        for b in log_y_branches:
            b_act = active_log_df[active_log_df['location'] == b] if not active_log_df.empty else pd.DataFrame()
            b_workable = b_act[b_act['user_max_stage'] < 4] if not b_act.empty else pd.DataFrame()
            
            log_workable_totals.append(b_workable.shape[0])
            # Exclusive logic: Max stage is 1 or 2 (Tie with us is considered safe)
            log_exc_vals.append(b_workable[b_workable['user_max_stage'] <= 2].shape[0] if not b_workable.empty else 0)
            # Flight Risk logic: Max stage is 3
            log_csan_vals.append(b_workable[b_workable['user_max_stage'] == 3].shape[0] if not b_workable.empty else 0)

        branch_loss_labels = [f"<b>{b}</b><br>{t} Workable" for b, t in zip(log_y_branches, log_workable_totals)]

        exc_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(log_exc_vals, log_workable_totals)]
        csan_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(log_csan_vals, log_workable_totals)]

        exc_labels = [f"{p:.0f}%" if p > 0 else "" for p in exc_pct_num]
        csan_labels = [f"{p:.0f}%" if p > 0 else "" for p in csan_pct_num]

        fig_loss_log = go.Figure()
        fig_loss_log.add_trace(go.Bar(name="✅ Exclusive (Safe)", y=branch_loss_labels, x=exc_pct_num, orientation='h', marker_color="#a7f3d0", text=exc_labels, textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="#0f172a")))
        fig_loss_log.add_trace(go.Bar(name="🚨 In Competitor Sanction", y=branch_loss_labels, x=csan_pct_num, orientation='h', marker_color="#9f1239", text=csan_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))

        fig_loss_log.update_layout(barmode="stack", height=380, margin=dict(t=40, b=20, l=20, r=20), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]), yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b"), autorange="reversed"))
        st.plotly_chart(fig_loss_log, width="stretch")
        
        st.divider()

        # --- ROW 4: QUERY RESOLUTION STATUS ---
        st.markdown('<div class="section-header"><h2>❓ 4. Query Resolution Status (Workable Login Leads)</h2></div>', unsafe_allow_html=True)
        st.markdown("Tracking resolved vs. unresolved queries for **Active Workable** Login leads.")

        res_vals, unres_vals, query_totals, branch_query_labels = [], [], [], []

        for b in log_y_branches:
            b_act = active_log_df[active_log_df['location'] == b] if not active_log_df.empty else pd.DataFrame()
            b_workable = b_act[b_act['user_max_stage'] < 4] if not b_act.empty else pd.DataFrame()
            
            if not b_workable.empty and 'latest_query' in b_workable.columns and 'query_status' in b_workable.columns:
                b_queried = b_workable[b_workable['latest_query'].notna() & (b_workable['latest_query'].astype(str).str.strip() != "")]
                total_q = b_queried.shape[0]
                resolved_c = b_queried[b_queried['query_status'].astype(str).str.strip().str.lower() == 'resolved'].shape[0]
                unresolved_c = b_queried[b_queried['query_status'].astype(str).str.strip().str.lower() == 'unresolved'].shape[0]
            else:
                total_q, resolved_c, unresolved_c = 0, 0, 0
                
            query_totals.append(total_q)
            res_vals.append(resolved_c)
            unres_vals.append(unresolved_c)
            branch_query_labels.append(f"<b>{b}</b><br>{total_q} Queries")

        res_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(res_vals, query_totals)]
        unres_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(unres_vals, query_totals)]
        res_labels = [f"{p:.0f}%" if p > 0 else "" for p in res_pct_num]
        unres_labels = [f"{p:.0f}%" if p > 0 else "" for p in unres_pct_num]

        fig_query_log = go.Figure()
        fig_query_log.add_trace(go.Bar(name="✅ Resolved", y=branch_query_labels, x=res_pct_num, orientation='h', marker_color="#a7f3d0", text=res_labels, textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="#0f172a")))
        fig_query_log.add_trace(go.Bar(name="⏳ Unresolved", y=branch_query_labels, x=unres_pct_num, orientation='h', marker_color="#fca5a5", text=unres_labels, textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="#9f1239")))

        fig_query_log.update_layout(barmode="stack", height=350, margin=dict(t=40, b=20, l=20, r=20), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]), yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b"), autorange="reversed"))
        st.plotly_chart(fig_query_log, width="stretch")
        
        st.divider()

        # --- ROW 5: LOST POTENTIAL ANALYSIS ---
        st.markdown('<div class="section-header"><h2>🚨 5. Lost Potential Analysis (Branch-wise)</h2></div>', unsafe_allow_html=True)
        st.markdown("For files formally lost from Login, this tracks what stage the competitor reached. *(Competitor Login is excluded since we already tied them at that stage)*.")

        true_dead_vals, comp_san_vals, comp_pf_vals = [], [], []
        lost_branch_totals, branch_lost_labels, potential_loss_pcts = [], [], []

        for b in log_y_branches:
            b_lost = lost_log_df[lost_log_df['location'] == b] if not lost_log_df.empty else pd.DataFrame()
            tot_lost = b_lost.shape[0]
            
            # td includes user_max_stage 1 or 2
            td = b_lost[b_lost['user_max_stage'] <= 2].shape[0] if not b_lost.empty else 0
            csan = b_lost[b_lost['user_max_stage'] == 3].shape[0] if not b_lost.empty else 0
            cpf = b_lost[b_lost['user_max_stage'] == 4].shape[0] if not b_lost.empty else 0
            
            lost_branch_totals.append(tot_lost)
            true_dead_vals.append(td)
            comp_san_vals.append(csan)
            comp_pf_vals.append(cpf)
            branch_lost_labels.append(f"<b>{b}</b><br>{tot_lost} Lost Leads")
            potential_loss_pcts.append(f"{((tot_lost - td) / tot_lost) * 100:.1f}%" if tot_lost > 0 else "0%")

        td_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(true_dead_vals, lost_branch_totals)]
        cs_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(comp_san_vals, lost_branch_totals)]
        cp_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(comp_pf_vals, lost_branch_totals)]

        td_labels = [f"{p:.0f}%" if p > 0 else "" for p in td_pct_num]
        cs_labels = [f"{p:.0f}%" if p > 0 else "" for p in cs_pct_num]
        cp_labels = [f"{p:.0f}%" if p > 0 else "" for p in cp_pct_num]

        fig_lost_log = go.Figure()
        fig_lost_log.add_trace(go.Bar(name="True Dead", y=branch_lost_labels, x=td_pct_num, orientation='h', marker_color="#e2e8f0", text=td_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")))
        fig_lost_log.add_trace(go.Bar(name="In Comp Sanction", y=branch_lost_labels, x=cs_pct_num, orientation='h', marker_color="#f97316", text=cs_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))
        fig_lost_log.add_trace(go.Bar(name="Comp PF Paid", y=branch_lost_labels, x=cp_pct_num, orientation='h', marker_color="#9f1239", text=cp_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))

        for i, b in enumerate(branch_lost_labels):
            if lost_branch_totals[i] > 0:
                fig_lost_log.add_annotation(x=100, y=b, text=f"<span style='color:#64748b; font-size:11px; font-weight:normal;'>Lost Potential</span><br><b style='font-size:16px; color:#9f1239;'>⚠️ {potential_loss_pcts[i]}</b>", showarrow=False, xanchor="left", xshift=15, align="left")

        fig_lost_log.update_layout(barmode="stack", height=380, margin=dict(t=40, b=20, l=20, r=100), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False, range=[0, 125]), yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b"), autorange="reversed"))
        st.plotly_chart(fig_lost_log, width="stretch")
        
        st.divider()

        # --- ROW 6: FLIGHT RISK AUTOPSY ---
        st.markdown('<div class="section-header"><h2>🕵️ 6. Flight Risk Autopsy (Why Did We Lose Them?)</h2></div>', unsafe_allow_html=True)
        st.markdown("For leads lost from Login that **progressed further** with a competitor (Potential Loss), this shows our team's tagged reason.")

        # Flight risk strictly means > 2 for Login leads
        log_flight_risk_df = lost_log_df[lost_log_df['user_max_stage'] > 2].copy() if not lost_log_df.empty else pd.DataFrame()

        if log_flight_risk_df.empty or 'lost_reason' not in log_flight_risk_df.columns:
            st.info("No flight risk leads found with recorded reasons for this selection.")
        else:
            top_reasons = log_flight_risk_df['lost_reason'].value_counts().head(4).index.tolist()
            branch_reason_labels = []
            reason_data = {r: [] for r in top_reasons}
            reason_data["Other"] = []
            branch_fr_totals = []

            for b in log_y_branches:
                b_fr = log_flight_risk_df[log_flight_risk_df['location'] == b]
                tot_fr = b_fr.shape[0]
                branch_fr_totals.append(tot_fr)
                branch_reason_labels.append(f"<b>{b}</b><br>{tot_fr} Flight Risk")
                
                if tot_fr > 0:
                    for r in top_reasons:
                        reason_data[r].append(b_fr[b_fr['lost_reason'] == r].shape[0])
                    other_count = b_fr[~b_fr['lost_reason'].isin(top_reasons)].shape[0]
                    reason_data["Other"].append(other_count)
                else:
                    for r in top_reasons:
                        reason_data[r].append(0)
                    reason_data["Other"].append(0)
            
            fig_reasons_log = go.Figure()
            reason_colors = ["#3b82f6", "#8b5cf6", "#f59e0b", "#10b981", "#94a3b8"] 
            
            for idx, r in enumerate(top_reasons + ["Other"]):
                raw_vals = reason_data[r]
                pct_vals = [(v/t)*100 if t > 0 else 0 for v, t in zip(raw_vals, branch_fr_totals)]
                labels = [f"{p:.0f}%" if p > 0 else "" for p in pct_vals]
                
                if sum(raw_vals) > 0:
                    fig_reasons_log.add_trace(go.Bar(
                        name=r, y=branch_reason_labels, x=pct_vals, orientation='h', marker_color=reason_colors[idx % len(reason_colors)], text=labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")
                    ))
            
            fig_reasons_log.update_layout(barmode="stack", height=380, margin=dict(t=40, b=20, l=20, r=20), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]), yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b"), autorange="reversed"))
            st.plotly_chart(fig_reasons_log, width="stretch")

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
        san_y_branches = [b for b in top_branches if b != "Others"]

        st.markdown('<div class="section-header"><h2>🗂️ Sanction Stage Lead Distribution</h2></div>', unsafe_allow_html=True)
        card_cols = st.columns(6)
        for i, col in enumerate(card_cols):
            if i < len(top_branches):
                with col:
                    st.metric(label=f"📍 {top_branches[i]}", value=f"{san_vols[i]:,}", delta=f"{san_pcts[i]} Share", delta_color="off")
        st.divider()

        # --- DATA ENGINE FOR TAB 4 ---
        conv_rates, tat_days = [], []
        active_san_counts, lost_san_counts = [], []
        san_u7_vals, san_o7_vals, san_term_vals = [], [], []

        active_san_df = san_df[san_df['lender_stage'] == 'Sanction'].copy() if 'lender_stage' in san_df.columns else pd.DataFrame()
        if not active_san_df.empty and 'sanction_date' in active_san_df.columns:
            active_san_df['aging_days'] = (pd.to_datetime('today') - active_san_df['sanction_date']).dt.days
        else:
            active_san_df['aging_days'] = 0
            
        lost_san_df = san_df[san_df['lost_category'].astype(str).str.contains('Sanction', case=False, na=False)] if 'lost_category' in san_df.columns else pd.DataFrame()

        for b in san_y_branches:
            b_df = san_df[san_df['location'] == b]
            san_c = b_df.shape[0]
            pf_c = b_df['pf_date'].notnull().sum() if 'pf_date' in b_df.columns else 0
            
            conv_rates.append(round((pf_c/san_c)*100, 1) if san_c > 0 else 0)
            tat_days.append(round(b_df['tat_sanc_pf'].mean(), 1) if not b_df.empty and 'tat_sanc_pf' in b_df.columns and not pd.isna(b_df['tat_sanc_pf'].mean()) else 0)
            
            b_act = active_san_df[active_san_df['location'] == b] if not active_san_df.empty else pd.DataFrame()
            b_lost = lost_san_df[lost_san_df['location'] == b] if not lost_san_df.empty else pd.DataFrame()
            
            active_san_counts.append(b_act.shape[0])
            lost_san_counts.append(b_lost.shape[0])
            
            u7 = b_act[(b_act['aging_days'] < 7) & (b_act['user_max_stage'] < 4)].shape[0] if not b_act.empty else 0
            o7 = b_act[(b_act['aging_days'] >= 7) & (b_act['user_max_stage'] < 4)].shape[0] if not b_act.empty else 0
            term = b_act[b_act['user_max_stage'] == 4].shape[0] if not b_act.empty else 0
            
            san_u7_vals.append(u7)
            san_o7_vals.append(o7)
            san_term_vals.append(term)

        # --- ROW 1: CONVERSION, TAT & VOLUMES (4-COLUMN GRID) ---
        st.markdown('<div class="section-header"><h2>📊 1. Branch Performance Matrix</h2></div>', unsafe_allow_html=True)
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        
        with col_c1:
            tot_s = san_df.shape[0] if not san_df.empty else 0
            tot_l = san_df['pf_date'].notnull().sum() if not san_df.empty and 'pf_date' in san_df.columns else 0
            lender_avg_conv = round((tot_l / tot_s)*100, 1) if tot_s > 0 else 0
            
            st.markdown(f"<div style='min-height: 80px;'><h4 style='text-align: center; margin-bottom:0px; color: #475569;'>Sanction ➔ PF Rate<br><span style='font-size:14px; font-weight:normal;'>(Lender Avg: {lender_avg_conv}%)</span></h4></div>", unsafe_allow_html=True)
            conv_colors = ["#9f1239" if val < lender_avg_conv else "#cbd5e1" for val in conv_rates]
            fig_conv = go.Figure(go.Bar(y=san_y_branches, x=conv_rates, orientation='h', marker_color=conv_colors, text=[f"{v}%" for v in conv_rates], textposition="inside", insidetextanchor="middle", textfont=dict(color=["white" if c == "#9f1239" else "#0f172a" for c in conv_colors], weight="bold")))
            fig_conv.add_vline(x=lender_avg_conv, line_dash="dash", line_color="#475569", line_width=2)
            fig_conv.update_layout(height=320, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569")))
            st.plotly_chart(fig_conv, width="stretch")

        with col_c2:
            lender_avg_tat = round(san_df['tat_sanc_pf'].mean(), 1) if not san_df.empty and 'tat_sanc_pf' in san_df.columns and not pd.isna(san_df['tat_sanc_pf'].mean()) else 0
            
            st.markdown(f"<div style='min-height: 80px;'><h4 style='text-align: center; margin-bottom:0px; color: #475569;'>Sanction ➔ PF TAT<br><span style='font-size:14px; font-weight:normal;'>(Lender Avg: {lender_avg_tat} Days)</span></h4></div>", unsafe_allow_html=True)
            tat_colors = ["#9f1239" if val > lender_avg_tat else "#cbd5e1" for val in tat_days]
            fig_tat = go.Figure(go.Bar(y=san_y_branches, x=tat_days, orientation='h', marker_color=tat_colors, text=[f"{v} days" for v in tat_days], textposition="inside", insidetextanchor="middle", textfont=dict(color=["white" if c == "#9f1239" else "#0f172a" for c in tat_colors], weight="bold")))
            fig_tat.add_vline(x=lender_avg_tat, line_dash="dash", line_color="#475569", line_width=2)
            fig_tat.update_layout(height=320, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
            st.plotly_chart(fig_tat, width="stretch")

        with col_c3:
            st.markdown("<div style='min-height: 80px;'><h4 style='text-align: center; margin-bottom:0px; color: #475569;'>Current Active Leads<br><span style='font-size:14px; font-weight:normal;'>(Sitting in Sanction)</span></h4></div>", unsafe_allow_html=True)
            fig_act = go.Figure(go.Bar(y=san_y_branches, x=active_san_counts, orientation='h', marker_color="#3b82f6", text=[f"{v}" for v in active_san_counts], textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="white")))
            fig_act.update_layout(height=320, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
            st.plotly_chart(fig_act, width="stretch")

        with col_c4:
            st.markdown("<div style='min-height: 80px;'><h4 style='text-align: center; margin-bottom:0px; color: #475569;'>Total Lost Leads<br><span style='font-size:14px; font-weight:normal;'>(Lost from Sanction)</span></h4></div>", unsafe_allow_html=True)
            fig_lst = go.Figure(go.Bar(y=san_y_branches, x=lost_san_counts, orientation='h', marker_color="#ef4444", text=[f"{v}" for v in lost_san_counts], textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="white")))
            fig_lst.update_layout(height=320, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"))
            st.plotly_chart(fig_lst, width="stretch")

        st.divider()

        # --- ROW 2: ACTIVE PIPELINE HEALTH ---
        st.markdown('<div class="section-header"><h2>⏱️ 2. Active Pipeline Health (Branch-wise)</h2></div>', unsafe_allow_html=True)
        st.markdown("A macro view of your **Active Sanction** pipeline. Breaking down healthy leads vs. aging bottlenecks vs. terminal competitor leakage.")

        totals_health_san = [u + o + c for u, o, c in zip(san_u7_vals, san_o7_vals, san_term_vals)]
        branch_health_labels = [f"<b>{b}</b><br>{t} Active" for b, t in zip(san_y_branches, totals_health_san)]

        u7_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(san_u7_vals, totals_health_san)]
        o7_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(san_o7_vals, totals_health_san)]
        term_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(san_term_vals, totals_health_san)]

        u7_labels = [f"{p:.0f}%" if p > 0 else "" for p in u7_pct_num]
        o7_labels = [f"{p:.0f}%" if p > 0 else "" for p in o7_pct_num]
        term_labels = [f"{p:.0f}%" if p > 0 else "" for p in term_pct_num]

        fig_health_san = go.Figure()
        fig_health_san.add_trace(go.Bar(name="< 7 Days (Active)", y=branch_health_labels, x=u7_pct_num, orientation='h', marker_color="#a7f3d0", text=u7_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="#0f172a", weight="bold")))
        fig_health_san.add_trace(go.Bar(name="> 7 Days (Aging)", y=branch_health_labels, x=o7_pct_num, orientation='h', marker_color="#fed7aa", text=o7_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="#0f172a", weight="bold")))
        fig_health_san.add_trace(go.Bar(name="Terminal Loss to Competitor", y=branch_health_labels, x=term_pct_num, orientation='h', marker_color="#9f1239", text=term_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))

        fig_health_san.update_layout(barmode="stack", height=380, margin=dict(t=40, b=20, l=20, r=20), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]), yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b"), autorange="reversed"))
        st.plotly_chart(fig_health_san, width="stretch")
        
        st.divider()

        # --- ROW 4: QUERY RESOLUTION STATUS ---
        st.markdown('<div class="section-header"><h2>❓ 3. Query Resolution Status (Workable Sanction Leads)</h2></div>', unsafe_allow_html=True)
        st.markdown("Tracking resolved vs. unresolved queries for **Active Workable** Sanction leads.")

        res_vals, unres_vals, query_totals, branch_query_labels = [], [], [], []

        for b in san_y_branches:
            b_act = active_san_df[active_san_df['location'] == b] if not active_san_df.empty else pd.DataFrame()
            b_workable = b_act[b_act['user_max_stage'] < 4] if not b_act.empty else pd.DataFrame()
            
            if not b_workable.empty and 'latest_query' in b_workable.columns and 'query_status' in b_workable.columns:
                b_queried = b_workable[b_workable['latest_query'].notna() & (b_workable['latest_query'].astype(str).str.strip() != "")]
                total_q = b_queried.shape[0]
                resolved_c = b_queried[b_queried['query_status'].astype(str).str.strip().str.lower() == 'resolved'].shape[0]
                unresolved_c = b_queried[b_queried['query_status'].astype(str).str.strip().str.lower() == 'unresolved'].shape[0]
            else:
                total_q, resolved_c, unresolved_c = 0, 0, 0
                
            query_totals.append(total_q)
            res_vals.append(resolved_c)
            unres_vals.append(unresolved_c)
            branch_query_labels.append(f"<b>{b}</b><br>{total_q} Queries")

        res_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(res_vals, query_totals)]
        unres_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(unres_vals, query_totals)]
        res_labels = [f"{p:.0f}%" if p > 0 else "" for p in res_pct_num]
        unres_labels = [f"{p:.0f}%" if p > 0 else "" for p in unres_pct_num]

        fig_query_san = go.Figure()
        fig_query_san.add_trace(go.Bar(name="✅ Resolved", y=branch_query_labels, x=res_pct_num, orientation='h', marker_color="#a7f3d0", text=res_labels, textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="#0f172a")))
        fig_query_san.add_trace(go.Bar(name="⏳ Unresolved", y=branch_query_labels, x=unres_pct_num, orientation='h', marker_color="#fca5a5", text=unres_labels, textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="#9f1239")))

        fig_query_san.update_layout(barmode="stack", height=350, margin=dict(t=40, b=20, l=20, r=20), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]), yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b"), autorange="reversed"))
        st.plotly_chart(fig_query_san, width="stretch")
        
        st.divider()

        # --- ROW 5: LOST POTENTIAL ANALYSIS ---
        st.markdown('<div class="section-header"><h2>🚨 4. Lost Potential Analysis (Branch-wise)</h2></div>', unsafe_allow_html=True)
        st.markdown("For files formally lost from Sanction, this tracks what stage the competitor reached. *(Flight risk here strictly means they paid PF elsewhere)*.")

        true_dead_vals, comp_pf_vals = [], []
        lost_branch_totals, branch_lost_labels, potential_loss_pcts = [], [], []

        for b in san_y_branches:
            b_lost = lost_san_df[lost_san_df['location'] == b] if not lost_san_df.empty else pd.DataFrame()
            tot_lost = b_lost.shape[0]
            
            # td includes user_max_stage 1, 2, or 3
            td = b_lost[b_lost['user_max_stage'] <= 3].shape[0] if not b_lost.empty else 0
            cpf = b_lost[b_lost['user_max_stage'] == 4].shape[0] if not b_lost.empty else 0
            
            lost_branch_totals.append(tot_lost)
            true_dead_vals.append(td)
            comp_pf_vals.append(cpf)
            branch_lost_labels.append(f"<b>{b}</b><br>{tot_lost} Lost Leads")
            potential_loss_pcts.append(f"{((tot_lost - td) / tot_lost) * 100:.1f}%" if tot_lost > 0 else "0%")

        td_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(true_dead_vals, lost_branch_totals)]
        cp_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(comp_pf_vals, lost_branch_totals)]

        td_labels = [f"{p:.0f}%" if p > 0 else "" for p in td_pct_num]
        cp_labels = [f"{p:.0f}%" if p > 0 else "" for p in cp_pct_num]

        fig_lost_san = go.Figure()
        fig_lost_san.add_trace(go.Bar(name="True Dead", y=branch_lost_labels, x=td_pct_num, orientation='h', marker_color="#e2e8f0", text=td_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")))
        fig_lost_san.add_trace(go.Bar(name="Comp PF Paid", y=branch_lost_labels, x=cp_pct_num, orientation='h', marker_color="#9f1239", text=cp_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))

        for i, b in enumerate(branch_lost_labels):
            if lost_branch_totals[i] > 0:
                fig_lost_san.add_annotation(x=100, y=b, text=f"<span style='color:#64748b; font-size:11px; font-weight:normal;'>Lost Potential</span><br><b style='font-size:16px; color:#9f1239;'>⚠️ {potential_loss_pcts[i]}</b>", showarrow=False, xanchor="left", xshift=15, align="left")

        fig_lost_san.update_layout(barmode="stack", height=380, margin=dict(t=40, b=20, l=20, r=100), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False, range=[0, 125]), yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b"), autorange="reversed"))
        st.plotly_chart(fig_lost_san, width="stretch")
        
        st.divider()

        # --- ROW 6: FLIGHT RISK AUTOPSY ---
        st.markdown('<div class="section-header"><h2>🕵️ 5. Flight Risk Autopsy (Why Did We Lose Them?)</h2></div>', unsafe_allow_html=True)
        st.markdown("For leads lost from Sanction that **progressed further** with a competitor (Potential Loss), this shows our team's tagged reason.")

        # Flight risk strictly means > 3 for Sanction leads (Only PF Paid)
        san_flight_risk_df = lost_san_df[lost_san_df['user_max_stage'] > 3].copy() if not lost_san_df.empty else pd.DataFrame()

        if san_flight_risk_df.empty or 'lost_reason' not in san_flight_risk_df.columns:
            st.info("No flight risk leads found with recorded reasons for this selection.")
        else:
            top_reasons = san_flight_risk_df['lost_reason'].value_counts().head(4).index.tolist()
            branch_reason_labels = []
            reason_data = {r: [] for r in top_reasons}
            reason_data["Other"] = []
            branch_fr_totals = []

            for b in san_y_branches:
                b_fr = san_flight_risk_df[san_flight_risk_df['location'] == b]
                tot_fr = b_fr.shape[0]
                branch_fr_totals.append(tot_fr)
                branch_reason_labels.append(f"<b>{b}</b><br>{tot_fr} Flight Risk")
                
                if tot_fr > 0:
                    for r in top_reasons:
                        reason_data[r].append(b_fr[b_fr['lost_reason'] == r].shape[0])
                    other_count = b_fr[~b_fr['lost_reason'].isin(top_reasons)].shape[0]
                    reason_data["Other"].append(other_count)
                else:
                    for r in top_reasons:
                        reason_data[r].append(0)
                    reason_data["Other"].append(0)
            
            fig_reasons_san = go.Figure()
            reason_colors = ["#3b82f6", "#8b5cf6", "#f59e0b", "#10b981", "#94a3b8"] 
            
            for idx, r in enumerate(top_reasons + ["Other"]):
                raw_vals = reason_data[r]
                pct_vals = [(v/t)*100 if t > 0 else 0 for v, t in zip(raw_vals, branch_fr_totals)]
                labels = [f"{p:.0f}%" if p > 0 else "" for p in pct_vals]
                
                if sum(raw_vals) > 0:
                    fig_reasons_san.add_trace(go.Bar(
                        name=r, y=branch_reason_labels, x=pct_vals, orientation='h', marker_color=reason_colors[idx % len(reason_colors)], text=labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")
                    ))
            
            fig_reasons_san.update_layout(barmode="stack", height=380, margin=dict(t=40, b=20, l=20, r=20), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]), yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b"), autorange="reversed"))
            st.plotly_chart(fig_reasons_san, width="stretch")
