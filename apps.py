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
    
    # Flight Risk Engine (YOUR ORIGINAL LOGIC - UNTOUCHED)
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
        
    # ====================================================================
    # 🚨 NEW: COMPETITOR FLIGHT RISK ENGINE (comp_max_stage) 🚨
    # ====================================================================
    if 'user_id' in df.columns and 'bank_name' in df.columns and 'lender_stage' in df.columns:
        # 1. Map stages (Lost = 0 because they are out of the race)
        stage_map = {
            'bank prospect': 1, 
            'login': 2, 
            'sanction': 3, 
            'pf paid': 4, 
            'disbursement done': 4, 
            'lost': 0 
        }
        
        # Clean the string and map it
        temp_stage = df['lender_stage'].astype(str).str.strip().str.lower()
        df['comp_eval_stage'] = temp_stage.map(stage_map).fillna(0)

        # 2. Get the highest stage reached by EACH bank for EACH user
        bank_maxes = df.groupby(['user_id', 'bank_name'])['comp_eval_stage'].max().reset_index()

        # 3. Sort so the highest stages are at the top for each user
        bank_maxes = bank_maxes.sort_values(by=['user_id', 'comp_eval_stage'], ascending=[True, False])

        # 4. Rank them safely to find 1st place and 2nd place banks
        bank_maxes['rank'] = bank_maxes.groupby('user_id').cumcount() + 1
        
        # Extract the top 2 banks per user
        top_1 = bank_maxes[bank_maxes['rank'] == 1].set_index('user_id')
        top_2 = bank_maxes[bank_maxes['rank'] == 2].set_index('user_id')

        # Convert to fast dictionaries for lookup
        top_1_dict = top_1.to_dict('index')
        top_2_dict = top_2['comp_eval_stage'].to_dict()

        # 5. The assignment logic
        def get_comp_max(row):
            uid = row['user_id']
            bname = row['bank_name']
            
            # No competitors exist
            if uid not in top_1_dict: 
                return 0
                
            # If THIS row is the leading bank, the biggest threat is the 2nd place bank
            if bname == top_1_dict[uid]['bank_name']:
                return top_2_dict.get(uid, 0)
            
            # If THIS row is NOT the leading bank, the biggest threat is the 1st place bank
            return top_1_dict[uid]['comp_eval_stage']

        df['comp_max_stage'] = df.apply(get_comp_max, axis=1)
        
        # Cleanup temporary column
        df = df.drop(columns=['comp_eval_stage'])
    else:
        df['comp_max_stage'] = 0
    # ====================================================================
    
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
    # ==========================================
    # --- COMBINED SECTION 1 & 2: EXECUTIVE YOY MATRIX ---
    # ==========================================
    st.divider()
    st.markdown('<div class="section-header"><h2>🚀 1. YoY Executive Performance</h2></div>', unsafe_allow_html=True)
    st.markdown("Macro-level volume comparison and monthly pacing against the previous year's **Year-to-Date (YTD)** equivalents.")

    # 🚨 POINT THIS TO YOUR RAW, UNFILTERED DATA 🚨
    df_master = df.copy() 
    
    # Ensure ALL date columns are datetime objects
    for col in ['date_shared', 'login_date', 'sanction_date', 'pf_date']:
        if col in df_master.columns:
            df_master[col] = pd.to_datetime(df_master[col], errors='coerce')

    # ---------------------------------------------------------
    # PART A: HTML KPI CARDS (YTD VOLUMES)
    # ---------------------------------------------------------
    from datetime import datetime
    today = datetime.now()
    curr_month = today.month
    curr_day = today.day

    # Dynamic filter: Only count last year's leads up to today's exact date
    def get_ytd_mask(date_series, year):
        if date_series is None or date_series.empty:
            return pd.Series(False, index=df_master.index)
        return (date_series.dt.year == year) & \
               ((date_series.dt.month < curr_month) | \
                ((date_series.dt.month == curr_month) & (date_series.dt.day <= curr_day)))

    # Fall 25 YTD Totals (Apples-to-Apples comparison)
    f25_shr = df_master[get_ytd_mask(df_master['date_shared'], 2025)].shape[0] if 'date_shared' in df_master.columns else 0
    f25_log = df_master[get_ytd_mask(df_master['login_date'], 2025)].shape[0] if 'login_date' in df_master.columns else 0
    f25_san = df_master[get_ytd_mask(df_master['sanction_date'], 2025)].shape[0] if 'sanction_date' in df_master.columns else 0
    f25_pf = df_master[get_ytd_mask(df_master['pf_date'], 2025)].shape[0] if 'pf_date' in df_master.columns else 0

    # Fall 26 Current Totals
    f26_shr = df_master[df_master['date_shared'].dt.year == 2026].shape[0] if 'date_shared' in df_master.columns else 0
    f26_log = df_master[df_master['login_date'].dt.year == 2026].shape[0] if 'login_date' in df_master.columns else 0
    f26_san = df_master[df_master['sanction_date'].dt.year == 2026].shape[0] if 'sanction_date' in df_master.columns else 0
    f26_pf = df_master[df_master['pf_date'].dt.year == 2026].shape[0] if 'pf_date' in df_master.columns else 0

    # YoY Percentage Logic
    def get_yoy_html(curr, prev):
        if prev == 0: return f"<span style='background-color:#dcfce3; color:#166534; padding:2px 8px; border-radius:12px; font-size:12px; font-weight:700;'>+100%</span>"
        pct = ((curr - prev) / prev) * 100
        if pct >= 0:
            return f"<span style='background-color:#dcfce3; color:#166534; padding:2px 8px; border-radius:12px; font-size:12px; font-weight:700;'>▲ +{pct:.1f}%</span>"
        else:
            return f"<span style='background-color:#fee2e2; color:#991b1b; padding:2px 8px; border-radius:12px; font-size:12px; font-weight:700;'>▼ {pct:.1f}%</span>"

    html_shr_yoy = get_yoy_html(f26_shr, f25_shr)
    html_log_yoy = get_yoy_html(f26_log, f25_log)
    html_san_yoy = get_yoy_html(f26_san, f25_san)
    html_pf_yoy = get_yoy_html(f26_pf, f25_pf)

    # The 4-Stage HTML Matrix (Flattened to prevent Markdown code block rendering)
    raw_kpi_html = f"""
    <div style="display: flex; gap: 20px; margin-bottom: 20px;">
        <div style="flex: 1; background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); border-top: 4px solid #6366f1;">
            <div style="color: #64748b; font-size: 13px; font-weight: 600; text-transform: uppercase; margin-bottom: 8px;">Total Shared (BP)</div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="font-size: 32px; font-weight: 800; color: #0f172a;">{f26_shr:,}</div>
                <div>{html_shr_yoy}</div>
            </div>
            <div style="color: #94a3b8; font-size: 13px; margin-top: 4px;">Fall 25 YTD: {f25_shr:,}</div>
        </div>
        <div style="flex: 1; background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); border-top: 4px solid #2563eb;">
            <div style="color: #64748b; font-size: 13px; font-weight: 600; text-transform: uppercase; margin-bottom: 8px;">Total Logins</div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="font-size: 32px; font-weight: 800; color: #0f172a;">{f26_log:,}</div>
                <div>{html_log_yoy}</div>
            </div>
            <div style="color: #94a3b8; font-size: 13px; margin-top: 4px;">Fall 25 YTD: {f25_log:,}</div>
        </div>
        <div style="flex: 1; background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); border-top: 4px solid #8b5cf6;">
            <div style="color: #64748b; font-size: 13px; font-weight: 600; text-transform: uppercase; margin-bottom: 8px;">Total Sanctions</div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="font-size: 32px; font-weight: 800; color: #0f172a;">{f26_san:,}</div>
                <div>{html_san_yoy}</div>
            </div>
            <div style="color: #94a3b8; font-size: 13px; margin-top: 4px;">Fall 25 YTD: {f25_san:,}</div>
        </div>
        <div style="flex: 1; background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); border-top: 4px solid #10b981;">
            <div style="color: #64748b; font-size: 13px; font-weight: 600; text-transform: uppercase; margin-bottom: 8px;">Total PF Paid</div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="font-size: 32px; font-weight: 800; color: #0f172a;">{f26_pf:,}</div>
                <div>{html_pf_yoy}</div>
            </div>
            <div style="color: #94a3b8; font-size: 13px; margin-top: 4px;">Fall 25 YTD: {f25_pf:,}</div>
        </div>
    </div>
    """
    st.markdown(raw_kpi_html.replace('\n', '').strip(), unsafe_allow_html=True)


    # ---------------------------------------------------------
    # PART B: PREMIUM MONTHLY PACING MATRIX (JAN - AUG)
    # ---------------------------------------------------------
    st.markdown("<h4 style='color: #334155; font-size: 16px; font-weight: 700; margin-top: 35px; margin-bottom: 15px;'>YoY Monthly Login Pacing & Growth</h4>", unsafe_allow_html=True)

    month_nums = [1, 2, 3, 4, 5, 6, 7, 8]
    month_names = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG']

    m_f25_log, m_f26_log = [], []
    for m in month_nums:
        m_f25_log.append(df_master[(df_master['login_date'].dt.month == m) & (df_master['login_date'].dt.year == 2025)].shape[0])
        m_f26_log.append(df_master[(df_master['login_date'].dt.month == m) & (df_master['login_date'].dt.year == 2026)].shape[0])

    # Calculate global max to accurately scale the mini-bars across all cards
    global_max = max(max(m_f25_log) if m_f25_log else 0, max(m_f26_log) if m_f26_log else 0)
    if global_max == 0: global_max = 1 # Prevent division by zero

    cards_html = ""
    for i in range(8):
        v25 = m_f25_log[i]
        v26 = m_f26_log[i]
        m_name = month_names[i]

        # Dynamic Growth Pill Logic
        if v25 == 0 and v26 > 0:
            growth_html = "<span style='background:#dcfce3; color:#166534; font-size:11px; padding:3px 8px; border-radius:12px; font-weight:700; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>▲ MAX</span>"
        elif v25 == 0 and v26 == 0:
            growth_html = "<span style='background:#f1f5f9; color:#64748b; font-size:11px; padding:3px 8px; border-radius:12px; font-weight:700; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>-</span>"
        else:
            pct = ((v26 - v25) / v25) * 100
            if pct > 0:
                growth_html = f"<span style='background:#dcfce3; color:#166534; font-size:11px; padding:3px 8px; border-radius:12px; font-weight:700; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>▲ {pct:.0f}%</span>"
            elif pct < 0:
                growth_html = f"<span style='background:#fee2e2; color:#991b1b; font-size:11px; padding:3px 8px; border-radius:12px; font-weight:700; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>▼ {abs(pct):.0f}%</span>"
            else:
                growth_html = f"<span style='background:#f1f5f9; color:#64748b; font-size:11px; padding:3px 8px; border-radius:12px; font-weight:700; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>0%</span>"

        # Math for the inline Micro-Bars
        w25 = (v25 / global_max) * 100
        w26 = (v26 / global_max) * 100

        # Building the individual month card
        cards_html += f"""
        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px; box-shadow: 0 2px 4px -1px rgba(0, 0, 0, 0.02), 0 1px 2px -1px rgba(0, 0, 0, 0.02); transition: transform 0.2s, box-shadow 0.2s;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 10px 15px -3px rgba(0, 0, 0, 0.05)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px -1px rgba(0, 0, 0, 0.02)'">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-weight: 800; color: #475569; font-size: 13px; letter-spacing: 0.5px;">{m_name}</span>
                {growth_html}
            </div>
            <div style="margin-bottom: 15px;">
                <div style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 26px; font-weight: 800; color: #0f172a; line-height: 1; margin-bottom: 4px;">{v26:,}</div>
                <div style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 12px; color: #94a3b8; font-weight: 500;">vs {v25:,} last yr</div>
            </div>
            <div style="display: flex; flex-direction: column; gap: 6px;">
                <div style="display: flex; align-items: center; gap: 6px;" title="Fall 26: {v26:,} Logins">
                    <div style="width: 100%; height: 6px; background: #f1f5f9; border-radius: 3px; overflow: hidden;">
                        <div style="width: {w26}%; height: 100%; background: #2563eb; border-radius: 3px;"></div>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 6px;" title="Fall 25: {v25:,} Logins">
                    <div style="width: 100%; height: 6px; background: #f1f5f9; border-radius: 3px; overflow: hidden;">
                        <div style="width: {w25}%; height: 100%; background: #cbd5e1; border-radius: 3px;"></div>
                    </div>
                </div>
            </div>
        </div>
        """

    # Wrap the 8 cards in a responsive CSS Grid
    grid_html = f"""
    <div style="background: linear-gradient(145deg, #ffffff, #f8fafc); border: 1px solid #e2e8f0; border-radius: 12px; padding: 25px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); margin-bottom: 30px;">
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 15px; margin-bottom: 20px;">
            {cards_html}
        </div>
        <div style="display: flex; gap: 15px; justify-content: flex-end; font-family: ui-sans-serif, system-ui, sans-serif; font-size: 11px; color: #64748b; font-weight: 600;">
            <div style="display: flex; align-items: center; gap: 5px;"><div style="width: 8px; height: 8px; background: #2563eb; border-radius: 2px;"></div> Fall 26 Current</div>
            <div style="display: flex; align-items: center; gap: 5px;"><div style="width: 8px; height: 8px; background: #cbd5e1; border-radius: 2px;"></div> Fall 25 Baseline</div>
        </div>
    </div>
    """

    # Flatten HTML to bypass Streamlit markdown rendering bugs
    st.markdown(grid_html.replace('\n', '').strip(), unsafe_allow_html=True)
    st.divider()

    # --- SECTION 2: M-O-M PROGRESSION (PURE SVG SAAS TRACKER) ---
    st.markdown('<div class="section-header"><h2>📅 2. Fall 26 M-o-M Progression</h2></div>', unsafe_allow_html=True)
    
    from datetime import datetime
    current_month = datetime.now().month

    def get_monthly_counts(date_series, *args):
        target_month = args[0] if len(args) > 0 and isinstance(args[0], int) else current_month
        if date_series is None or date_series.empty:
            return [0] * target_month
        counts = date_series.dt.month.value_counts().reindex(range(1, target_month + 1)).fillna(0)
        return counts.tolist()

    shared_mom = get_monthly_counts(df_cohort['date_shared'] if 'date_shared' in df_cohort.columns else pd.Series(dtype='datetime64[ns]'), current_month)
    login_mom = get_monthly_counts(df_cohort['login_date'] if 'login_date' in df_cohort.columns else pd.Series(dtype='datetime64[ns]'), current_month)
    sanc_mom = get_monthly_counts(df_cohort['sanction_date'] if 'sanction_date' in df_cohort.columns else pd.Series(dtype='datetime64[ns]'), current_month)
    pf_mom = get_monthly_counts(df_cohort['pf_date'] if 'pf_date' in df_cohort.columns else pd.Series(dtype='datetime64[ns]'), current_month)

    all_months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    months_list = all_months[:len(shared_mom)]

    # --- SVG MAPPING ENGINE ---
    # We define the canvas size and calculate the scaling
    svg_w, svg_h = 800, 250
    max_val = max(shared_mom + login_mom + sanc_mom + pf_mom) if any([shared_mom, login_mom, sanc_mom, pf_mom]) else 1
    
    def get_coords(data):
        pts = []
        for i, val in enumerate(data):
            x = (i / (len(data) - 1)) * (svg_w - 60) + 30
            y = (svg_h - 40) - (val / max_val * (svg_h - 80))
            pts.append((x, y))
        return pts

    def build_svg_line(data, color, offset=0):
        coords = get_coords(data)
        path = "M " + " L ".join([f"{x},{y}" for x, y in coords])
        line = f'<path d="{path}" fill="none" stroke="{color}" stroke-width="3" />'
        
        # Add Circles and Text Labels
        points = ""
        for x, y in coords:
            points += f'<circle cx="{x}" cy="{y}" r="4" fill="{color}" />'
        
        # Add labels logic
        labels = ""
        for i, val in enumerate(data):
            x, y = coords[i]
            # Offset labels based on index (don't stack them)
            y_pos = y - 15 if i % 2 == 0 else y + 25
            labels += f'<text x="{x}" y="{y_pos}" text-anchor="middle" fill="{color}" font-size="12" font-weight="bold">{int(val)}</text>'
            
        return line + points + labels

    # Generate SVGs
    svg_shared = build_svg_line(shared_mom, "#4f46e5")
    svg_login = build_svg_line(login_mom, "#818cf8")
    svg_sanc = build_svg_line(sanc_mom, "#f59e0b")
    svg_pf = build_svg_line(pf_mom, "#10b981")

    # X-Axis Labels
    xaxis_labels = ""
    for i, m in enumerate(months_list):
        x = (i / (len(months_list) - 1)) * (svg_w - 60) + 30
        xaxis_labels += f'<text x="{x}" y="{svg_h - 10}" text-anchor="middle" fill="#64748b" font-size="12" font-weight="600">{m}</text>'

    final_card = f"""
    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 25px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
        <svg viewBox="0 0 {svg_w} {svg_h}" style="width: 100%; height: auto;">
            {svg_shared}
            {svg_login}
            {svg_sanc}
            {svg_pf}
            {xaxis_labels}
        </svg>
        
        <div style="display: flex; gap: 20px; justify-content: center; margin-top: 20px; padding-top: 15px; border-top: 1px solid #f1f5f9;">
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 10px; height: 10px; border-radius: 50%; background-color: #4f46e5;"></div><span style="color: #475569; font-size: 12px; font-weight: 700;">Shared</span></div>
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 10px; height: 10px; border-radius: 50%; background-color: #818cf8;"></div><span style="color: #475569; font-size: 12px; font-weight: 700;">Login</span></div>
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 10px; height: 10px; border-radius: 50%; background-color: #f59e0b;"></div><span style="color: #475569; font-size: 12px; font-weight: 700;">Sanction</span></div>
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 10px; height: 10px; border-radius: 50%; background-color: #10b981;"></div><span style="color: #475569; font-size: 12px; font-weight: 700;">PF Paid</span></div>
        </div>
    </div>
    """

    st.markdown(final_card.replace('\n', '').strip(), unsafe_allow_html=True)
    st.divider()
    
    # --- SECTION 2B: IN-MONTH CONVERSION VELOCITY (SVG LINE MATRIX) ---
    st.divider()
    st.markdown('<div class="section-header"><h2>📈 2B. In-Month Conversion Velocity (YoY)</h2></div>', unsafe_allow_html=True)
    st.markdown("Tracking **Strict Same-Month Cohorts**: Out of all raw leads that reached a stage in a given month, what percentage successfully moved to the next stage *within that exact same month*.")

    # ==========================================
    # 🚨 PURE LOGIC ENGINE (100% UNCHANGED) 🚨
    # ==========================================
    df_master = df.copy() 
    
    date_cols = ['date_shared', 'login_date', 'sanction_date', 'pf_date']
    for col in date_cols:
        if col in df_master.columns:
            df_master[col] = pd.to_datetime(df_master[col], errors='coerce')

    month_nums = [1, 2, 3, 4, 5, 6, 7, 8]
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug']

    f25_bp_log, f26_bp_log = [], []
    f25_log_san, f26_log_san = [], []
    f25_san_pf, f26_san_pf = [], []

    for m in month_nums:
        # FALL 25
        base_bp_25 = df_master[(df_master['date_shared'].dt.month == m) & (df_master['date_shared'].dt.year == 2025)]
        succ_log_25 = base_bp_25[(base_bp_25['login_date'].dt.month == m) & (base_bp_25['login_date'].dt.year == 2025)]
        f25_bp_log.append((len(succ_log_25) / len(base_bp_25) * 100) if len(base_bp_25) > 0 else None)

        base_log_25 = df_master[(df_master['login_date'].dt.month == m) & (df_master['login_date'].dt.year == 2025)]
        succ_san_25 = base_log_25[(base_log_25['sanction_date'].dt.month == m) & (base_log_25['sanction_date'].dt.year == 2025)]
        f25_log_san.append((len(succ_san_25) / len(base_log_25) * 100) if len(base_log_25) > 0 else None)

        base_san_25 = df_master[(df_master['sanction_date'].dt.month == m) & (df_master['sanction_date'].dt.year == 2025)]
        succ_pf_25 = base_san_25[(base_san_25['pf_date'].dt.month == m) & (base_san_25['pf_date'].dt.year == 2025)]
        f25_san_pf.append((len(succ_pf_25) / len(base_san_25) * 100) if len(base_san_25) > 0 else None)

        # FALL 26
        base_bp_26 = df_master[(df_master['date_shared'].dt.month == m) & (df_master['date_shared'].dt.year == 2026)]
        succ_log_26 = base_bp_26[(base_bp_26['login_date'].dt.month == m) & (base_bp_26['login_date'].dt.year == 2026)]
        f26_bp_log.append((len(succ_log_26) / len(base_bp_26) * 100) if len(base_bp_26) > 0 else None)

        base_log_26 = df_master[(df_master['login_date'].dt.month == m) & (df_master['login_date'].dt.year == 2026)]
        succ_san_26 = base_log_26[(base_log_26['sanction_date'].dt.month == m) & (base_log_26['sanction_date'].dt.year == 2026)]
        f26_log_san.append((len(succ_san_26) / len(base_log_26) * 100) if len(base_log_26) > 0 else None)

        base_san_26 = df_master[(df_master['sanction_date'].dt.month == m) & (df_master['sanction_date'].dt.year == 2026)]
        succ_pf_26 = base_san_26[(base_san_26['pf_date'].dt.month == m) & (base_san_26['pf_date'].dt.year == 2026)]
        f26_san_pf.append((len(succ_pf_26) / len(base_san_26) * 100) if len(base_san_26) > 0 else None)


    # ==========================================
    # 🎨 PURE SVG SPARKLINES UI ENGINE
    # ==========================================
    def create_velocity_svg(title, d26, d25, color, month_labels):
        svg_w, svg_h = 350, 180
        
        # Calculate max bounds (Capped at 100 since it's percentages, unless somehow over 100)
        all_vals = [v for v in d26 + d25 if pd.notna(v)]
        max_val = max(all_vals) if all_vals else 100
        y_max = max(100, max_val * 1.15) # Give it 15% breathing room at the top
        
        # Mathematical curve smoother (FIXED UNPACKING BUG)
        def get_spline_path(coords):
            if len(coords) < 2: return ""
            if len(coords) == 2: return f"M {coords[0][0]},{coords[0][1]} L {coords[1][0]},{coords[1][1]}"
            path = f"M {coords[0][0]},{coords[0][1]}"
            for i in range(len(coords) - 1):
                x0, y0, _ = coords[i]   # 🚨 FIX: Added ', _' to safely absorb the 3rd value (v)
                x1, y1, _ = coords[i+1] # 🚨 FIX: Added ', _' here too
                cp1x = (x0 + x1) / 2
                path += f" C {cp1x},{y0} {cp1x},{y1} {x1},{y1}"
            return path

        def get_path_and_points(data, line_color, is_dashed, is_f26):
            valid_pts = [(i, v) for i, v in enumerate(data) if pd.notna(v)]
            if not valid_pts: return "", ""
            
            coords = []
            for i, v in valid_pts:
                x = (i / (len(month_labels) - 1)) * (svg_w - 40) + 20
                y = (svg_h - 30) - (v / y_max * (svg_h - 60))
                coords.append((x, y, v))
            
            path_d = get_spline_path(coords)
            dash = 'stroke-dasharray="5,5"' if is_dashed else ''
            path_html = f'<path d="{path_d}" fill="none" stroke="{line_color}" stroke-width="3" {dash} />'
            
            pts_html = ""
            for x, y, v in coords:
                pts_html += f'<circle cx="{x}" cy="{y}" r="4" fill="{line_color}" title="{v:.1f}%" />'
                if is_f26:
                    pts_html += f'<text x="{x}" y="{y-12}" text-anchor="middle" fill="{line_color}" font-size="11" font-weight="800">{v:.0f}%</text>'
            
            return path_html, pts_html
        
        p25, pts25 = get_path_and_points(d25, "#cbd5e1", True, False)
        p26, pts26 = get_path_and_points(d26, color, False, True)
        
        # X-axis labels
        x_labels_html = ""
        for i, m in enumerate(month_labels):
            x = (i / (len(month_labels) - 1)) * (svg_w - 40) + 20
            x_labels_html += f'<text x="{x}" y="{svg_h - 5}" text-anchor="middle" fill="#94a3b8" font-size="11" font-weight="700">{m}</text>'
            
        return f'''
        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 25px 20px 20px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); display: flex; flex-direction: column;">
            <div style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 15px; font-weight: 800; color: {color}; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px; text-align: center;">{title}</div>
            <svg viewBox="0 0 {svg_w} {svg_h}" style="width: 100%; height: auto; overflow: visible; margin-top: 10px;">
                {p25} {pts25}
                {p26} {pts26}
                {x_labels_html}
            </svg>
        </div>
        '''

    # Generate the 3 Cards
    card1 = create_velocity_svg("BP ➔ Login", f26_bp_log, f25_bp_log, "#3b82f6", month_names)
    card2 = create_velocity_svg("Login ➔ Sanction", f26_log_san, f25_log_san, "#ea580c", month_names)
    card3 = create_velocity_svg("Sanction ➔ PF Paid", f26_san_pf, f25_san_pf, "#10b981", month_names)

    # Master CSS Grid Layout
    matrix_html = f"""
    <div style="background: linear-gradient(145deg, #ffffff, #f8fafc); border: 1px solid #e2e8f0; border-radius: 12px; padding: 25px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); margin-top: 15px;">
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px;">
            {card1}
            {card2}
            {card3}
        </div>
        
        <!-- Interactive Footer Legend -->
        <div style="display: flex; gap: 20px; justify-content: center; margin-top: 25px; padding-top: 15px; border-top: 1px dashed #cbd5e1; font-family: ui-sans-serif, system-ui, sans-serif; font-size: 12px; color: #64748b; font-weight: 600;">
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 14px; height: 3px; background: #475569; border-radius: 2px;"></div> Fall 26 Current</div>
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 14px; height: 2px; border-top: 2px dashed #cbd5e1;"></div> Fall 25 Baseline Target</div>
        </div>
    </div>
    """
    
    st.markdown(matrix_html.replace('\n', '').strip(), unsafe_allow_html=True)
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
    # --- DYNAMIC X-AXIS LABELS (Active/Lost at the bottom) ---
    stages = ['Shared', 'Login', 'Sanction', 'PF Paid'] # 🚨 ADDED THIS LINE
    dynamic_stages = []
    for i, stage_name in enumerate(stages):
        if i < 3: 
            label = f"<b>{stage_name}</b><br><span style='font-size: 13px;'><b style='color: #ef4444;'>{losts[i]:,} Lost</b> &nbsp;|&nbsp; <b style='color: #16a34a;'>{currents[i]:,} Active</b></span>"
        else: 
            label = f"<b>{stage_name}</b>"
        dynamic_stages.append(label)

    # --- DYNAMIC TEXT POSITIONING (For the big numbers only) ---
    max_vol = max(totals) if totals else 1
    dynamic_positions = ["outside" if v < (max_vol * 0.25) else "inside" for v in totals]
    
    custom_text = []
    for tot, pos in zip(totals, dynamic_positions):
        main_col = '#1e293b' if pos == 'outside' else 'white'
        txt = f"<b style='font-size: 32px; color: {main_col};'>{tot:,}</b>"
        custom_text.append(txt)
    
    fig_funnel = go.Figure(go.Funnel(
        orientation='v', 
        x=dynamic_stages, 
        y=totals, 
        text=custom_text, 
        textposition=dynamic_positions, 
        textinfo="text",
        marker={"color": ["#4f46e5", "#6366f1", "#818cf8", "#a5b4fc"], "line": {"width": [2, 2, 2, 2], "color": ["white"]*4}},
        connector={"line": {"color": "#e2e8f0", "dash": "solid", "width": 2}, "fillcolor": "rgba(226, 232, 240, 0.4)"}
    ))
    
    fig_funnel.update_traces(cliponaxis=False)
    
    bp_log_pct = (tot_login/tot_shared)*100 if tot_shared > 0 else 0
    log_san_pct = (tot_sanc/tot_login)*100 if tot_login > 0 else 0
    san_pf_pct = (tot_pf/tot_sanc)*100 if tot_sanc > 0 else 0
    
    aesthetic_style = dict(
        showarrow=False, 
        bgcolor="rgba(0,0,0,0)", 
        borderpad=0
    )
    
    # Removed the word "CONVERSION", updated color to sleek slate-blue (#64748b), and bumped y to 1.15
    fig_funnel.add_annotation(x=0.5, y=1.15, xref="x", yref="paper", text=f"<b style='font-size:22px; color:#64748b;'>{bp_log_pct:.0f}% ➔</b>", **aesthetic_style)
    fig_funnel.add_annotation(x=1.5, y=1.15, xref="x", yref="paper", text=f"<b style='font-size:22px; color:#64748b;'>{log_san_pct:.0f}% ➔</b>", **aesthetic_style)
    fig_funnel.add_annotation(x=2.5, y=1.15, xref="x", yref="paper", text=f"<b style='font-size:22px; color:#64748b;'>{san_pf_pct:.0f}% ➔</b>", **aesthetic_style)
    
    max_funnel_range = max(totals) * 0.6 if totals else 1600
    
    # Bumped top margin ('t': 140) to give the higher annotations total clearance from the funnel blocks
    fig_funnel.update_layout(
        height=400, 
        margin={"t": 140, "b": 80, "l": 20, "r": 100}, 
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

    # ==========================================
    # --- COMBINED SECTION 4: ACTIVE PIPELINE PROSPECTS ---
    # ==========================================
    st.divider()
    st.markdown('<div class="section-header"><h2>💸 4. Active Pipeline Prospects</h2></div>', unsafe_allow_html=True)
    st.markdown("A macro-level breakdown of your active leads based on competitor threat, followed by the aging health of your truly **workable** pipeline.")

    # ---------------------------------------------------------
    # PART 4A: COMPETITOR THREAT CARDS
    # ---------------------------------------------------------
    def render_pipeline_card(stage_name, active_df, stage_num):
        if active_df.empty: return
        tot = active_df.shape[0]
        if tot == 0: return

        dead_c = active_df[active_df['comp_max_stage'] == 4].shape[0]

        if stage_num == 3: 
            san_c = active_df[active_df['comp_max_stage'] == 3].shape[0] 
            log_c = 0 
            exc_c = active_df[active_df['comp_max_stage'] <= 2].shape[0] 
        elif stage_num == 2: 
            san_c = active_df[active_df['comp_max_stage'] == 3].shape[0]
            log_c = active_df[active_df['comp_max_stage'] == 2].shape[0] 
            exc_c = active_df[active_df['comp_max_stage'] <= 1].shape[0]
        else: 
            san_c = active_df[active_df['comp_max_stage'] == 3].shape[0]
            log_c = active_df[active_df['comp_max_stage'] == 2].shape[0]
            exc_c = active_df[active_df['comp_max_stage'] <= 1].shape[0]

        p_dead = (dead_c / tot) * 100
        p_san = (san_c / tot) * 100
        p_log = (log_c / tot) * 100
        p_exc = (exc_c / tot) * 100

        if stage_num == 3:
            grid_cols = 3
            metrics_html = f"""
                <div style="display: flex; flex-direction: column;">
                    <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 24px; font-weight: 800; color: #9f1239; line-height: 1; margin-bottom: 4px;">{p_dead:.0f}%</span>
                    <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Dead (PF)</span>
                </div>
                <div style="display: flex; flex-direction: column;">
                    <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 24px; font-weight: 800; color: #10b981; line-height: 1; margin-bottom: 4px;">{p_exc:.0f}%</span>
                    <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Exclusive (Safe)</span>
                </div>
                <div style="display: flex; flex-direction: column;">
                    <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 24px; font-weight: 800; color: #ea580c; line-height: 1; margin-bottom: 4px;">{p_san:.0f}%</span>
                    <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Tied (Comp Sanction)</span>
                </div>
            """
            bar_html = f"""
                <div style="width: {p_dead}%; background-color: #9f1239;" title="Dead: {dead_c}"></div>
                <div style="width: {p_exc}%; background-color: #10b981;" title="Exclusive: {exc_c}"></div>
                <div style="width: {p_san}%; background-color: #ea580c;" title="Comp Sanction: {san_c}"></div>
            """
        else:
            grid_cols = 4
            metrics_html = f"""
                <div style="display: flex; flex-direction: column;">
                    <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 24px; font-weight: 800; color: #9f1239; line-height: 1; margin-bottom: 4px;">{p_dead:.0f}%</span>
                    <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Dead (PF)</span>
                </div>
                <div style="display: flex; flex-direction: column;">
                    <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 24px; font-weight: 800; color: #10b981; line-height: 1; margin-bottom: 4px;">{p_exc:.0f}%</span>
                    <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Exclusive</span>
                </div>
                <div style="display: flex; flex-direction: column;">
                    <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 24px; font-weight: 800; color: #ca8a04; line-height: 1; margin-bottom: 4px;">{p_log:.0f}%</span>
                    <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Comp Login</span>
                </div>
                <div style="display: flex; flex-direction: column;">
                    <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 24px; font-weight: 800; color: #ea580c; line-height: 1; margin-bottom: 4px;">{p_san:.0f}%</span>
                    <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Comp Sanction</span>
                </div>
            """
            bar_html = f"""
                <div style="width: {p_dead}%; background-color: #9f1239;" title="Dead: {dead_c}"></div>
                <div style="width: {p_exc}%; background-color: #10b981;" title="Exclusive: {exc_c}"></div>
                <div style="width: {p_log}%; background-color: #fcd34d;" title="Comp Login: {log_c}"></div>
                <div style="width: {p_san}%; background-color: #ea580c;" title="Comp Sanction: {san_c}"></div>
            """

        raw_html = f"""
        <div style="background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 13px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px;">{stage_name} ACTIVE</span>
                <span style="font-family: ui-monospace, monospace; font-size: 12px; color: #64748b; background-color: #f1f5f9; padding: 3px 10px; border-radius: 12px; font-weight: 600;">{tot:,} Total Leads</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat({grid_cols}, 1fr); gap: 15px; margin-bottom: 15px;">
                {metrics_html}
            </div>
            <div style="width: 100%; height: 12px; display: flex; border-radius: 4px; overflow: hidden; background: #f1f5f9; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);">
                {bar_html}
            </div>
        </div>
        """
        st.markdown(raw_html.replace('\n', '').strip(), unsafe_allow_html=True)

    render_pipeline_card("BP", active_bp, 1)
    render_pipeline_card("LOGIN", active_log, 2)
    render_pipeline_card("SANCTION", active_san, 3)

    # ---------------------------------------------------------
    # PART 4B: WORKABLE PIPELINE AGING (THE NEW COMPONENT)
    # ---------------------------------------------------------
    st.markdown("<h4 style='color: #334155; font-size: 16px; font-weight: 700; margin-top: 30px; margin-bottom: 5px;'>Workable Pipeline Aging Health</h4>", unsafe_allow_html=True)
    
    # 1. Filter out Dead leads (Stage 4) to get purely workable pipelines
    work_bp = active_bp[active_bp['comp_max_stage'] < 4].copy() if not active_bp.empty else pd.DataFrame()
    work_log = active_log[active_log['comp_max_stage'] < 4].copy() if not active_log.empty else pd.DataFrame()
    work_san = active_san[active_san['comp_max_stage'] < 4].copy() if not active_san.empty else pd.DataFrame()

    # 2. Calculate accurate aging based on stage entry date
    today = pd.to_datetime('today')
    
    def calc_aging(df, date_col):
        if not df.empty and date_col in df.columns:
            return (today - pd.to_datetime(df[date_col], errors='coerce')).dt.days.fillna(0)
        return pd.Series(0, index=df.index if not df.empty else [])

    work_bp['aging'] = calc_aging(work_bp, 'date_shared')
    work_log['aging'] = calc_aging(work_log, 'login_date')
    work_san['aging'] = calc_aging(work_san, 'sanction_date')

    # 3. Bucket logic
    def get_aging_buckets(df):
        if df.empty: return [0, 0, 0, 0]
        b1 = df[(df['aging'] >= 0) & (df['aging'] <= 3)].shape[0]
        b2 = df[(df['aging'] >= 4) & (df['aging'] <= 7)].shape[0]
        b3 = df[(df['aging'] >= 8) & (df['aging'] <= 14)].shape[0]
        b4 = df[df['aging'] >= 15].shape[0]
        return [b1, b2, b3, b4]

    bp_buckets = get_aging_buckets(work_bp)
    log_buckets = get_aging_buckets(work_log)
    san_buckets = get_aging_buckets(work_san)

    # 4. Master Engine to render the responsive HTML vertical bar cards
    def render_aging_card(stage_name, buckets, total):
        max_val = max(buckets) if max(buckets) > 0 else 1
        heights = [(v/max_val)*65 for v in buckets] # Max height cap of 65px
        
        # Perfect SaaS Hex Colors mimicking your reference image
        colors = ["#a7f3d0", "#fde68a", "#d97706", "#9f1239"]
        labels = ["0–3d", "4–7d", "8–14d", "15d+"]
        
        bars_html = ""
        for i in range(4):
            val = buckets[i]
            h = max(heights[i], 4) # Ensures even a 0 has a tiny visible sliver so layout doesn't break
            bars_html += f"""
            <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
                <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 13px; font-weight: 800; color: #1e293b; margin-bottom: 5px;">{val}</span>
                <div style="width: 100%; height: {h}px; background-color: {colors[i]}; border-radius: 4px 4px 0 0; transition: height 0.4s ease;"></div>
                <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 11px; color: #64748b; margin-top: 8px; font-weight: 600;">{labels[i]}</span>
            </div>
            """
        
        return f"""
        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 22px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
            <div style="color: #94a3b8; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px;">{stage_name} WORKABLE</div>
            <div style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 42px; font-weight: 900; color: #0f172a; margin-bottom: 25px; line-height: 1; letter-spacing: -1px;">{total:,}</div>
            <div style="display: flex; gap: 8px; align-items: flex-end; height: 95px;">
                {bars_html}
            </div>
        </div>
        """

    # 5. Inject CSS Grid Wrapper
    grid_html = f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 10px; margin-top: 15px;">
        {render_aging_card("BP", bp_buckets, work_bp.shape[0])}
        {render_aging_card("LOGIN", log_buckets, work_log.shape[0])}
        {render_aging_card("SANCTION", san_buckets, work_san.shape[0])}
    </div>
    """
    
    st.markdown(grid_html.replace('\n', '').strip(), unsafe_allow_html=True)
    st.divider()
    
    # --- SECTION 6: LOST POTENTIAL ANALYSIS (HTML SAAS CARD) ---
    st.divider()
    st.markdown('<div class="section-header"><h2>🚨 6. Lost Potential Analysis</h2></div>', unsafe_allow_html=True)
    
    # Data Calculations (100% identical to your original logic)
    stages_names = ["Lost from Sanction", "Lost from Login", "Lost from BP"]
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

    rows_html = ""
    for i in range(3):
        tot = bar_totals[i]
        if tot == 0: continue

        td_c, cl_c, cs_c, cp_c = true_dead[i], comp_login[i], comp_sanc[i], comp_pf[i]
        
        # Percentages
        td_p = (td_c / tot) * 100
        cl_p = (cl_c / tot) * 100
        cs_p = (cs_c / tot) * 100
        cp_p = (cp_c / tot) * 100
        pot_loss_pct = ((tot - td_c) / tot) * 100

        # Build individual bar segments
        bar_html = ""
        
        # 1. True Dead (Gray)
        if td_p > 0: 
            txt = f"{td_p:.0f}%" if td_p >= 5 else ""
            bar_html += f'<div style="width: {td_p}%; background-color: #e2e8f0; display: flex; align-items: center; justify-content: center; color: #475569; font-size: 11px; font-weight: bold; transition: width 0.3s ease;" title="True Dead: {td_c} Leads ({td_p:.1f}%)">{txt}</div>'
        
        # 2. Comp Login (Yellow-Orange)
        if cl_p > 0: 
            txt = f"{cl_p:.0f}%" if cl_p >= 5 else ""
            bar_html += f'<div style="width: {cl_p}%; background-color: #fdba74; display: flex; align-items: center; justify-content: center; color: #9a3412; font-size: 11px; font-weight: bold; transition: width 0.3s ease;" title="In Comp Login: {cl_c} Leads ({cl_p:.1f}%)">{txt}</div>'
        
        # 3. Comp Sanction (Bright Orange)
        if cs_p > 0: 
            txt = f"{cs_p:.0f}%" if cs_p >= 5 else ""
            bar_html += f'<div style="width: {cs_p}%; background-color: #f97316; display: flex; align-items: center; justify-content: center; color: white; font-size: 11px; font-weight: bold; transition: width 0.3s ease;" title="In Comp Sanction: {cs_c} Leads ({cs_p:.1f}%)">{txt}</div>'
        
        # 4. Comp PF Paid (Dark Red)
        if cp_p > 0: 
            txt = f"{cp_p:.0f}%" if cp_p >= 5 else ""
            bar_html += f'<div style="width: {cp_p}%; background-color: #9f1239; display: flex; align-items: center; justify-content: center; color: white; font-size: 11px; font-weight: bold; transition: width 0.3s ease;" title="Comp PF Paid: {cp_c} Leads ({cp_p:.1f}%)">{txt}</div>'

        # Append row to HTML
        rows_html += f"""
        <div style="margin-bottom: 22px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 8px;">
                <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-weight: 700; color: #1e293b; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">{stages_names[i]}</span>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <span style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; color: #64748b; font-size: 12px; font-weight: 600; background-color: #f1f5f9; padding: 2px 8px; border-radius: 12px;">{tot} Total</span>
                    <span style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; color: #9f1239; font-size: 12px; font-weight: 700; background-color: #ffe4e6; padding: 2px 8px; border-radius: 12px;">⚠️ {pot_loss_pct:.1f}% Lost Potential</span>
                </div>
            </div>
            <div style="width: 100%; height: 28px; display: flex; border-radius: 6px; overflow: hidden; background-color: #f8fafc; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);">
                {bar_html}
            </div>
        </div>
        """

    # Master UI Wrapper
    final_html = f"""
    <div style="background: linear-gradient(145deg, #ffffff, #f8fafc); border: 1px solid #e2e8f0; border-radius: 12px; padding: 30px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); margin-top: 15px;">
        <div style="margin-bottom: 25px; border-bottom: 1px solid #f1f5f9; padding-bottom: 15px;">
            <h3 style="margin: 0; color: #0f172a; font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 22px;">📉</span> Competitor Funnel Tracking
            </h3>
            <p style="margin: 5px 0 0 0; color: #64748b; font-size: 13px;">Out of the total files lost at each stage, this tracks exactly what stage the competitor has reached with them.</p>
        </div>
        
        {rows_html}
        
        <!-- Interactive Legend -->
        <div style="display: flex; flex-wrap: wrap; gap: 15px; margin-top: 30px; padding-top: 15px; border-top: 1px dashed #cbd5e1; justify-content: center;">
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 12px; height: 12px; border-radius: 3px; background-color: #e2e8f0;"></div><span style="color: #475569; font-size: 12px; font-weight: 500;">True Dead (No Comp Action)</span></div>
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 12px; height: 12px; border-radius: 3px; background-color: #fdba74;"></div><span style="color: #475569; font-size: 12px; font-weight: 500;">In Comp Login</span></div>
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 12px; height: 12px; border-radius: 3px; background-color: #f97316;"></div><span style="color: #475569; font-size: 12px; font-weight: 500;">In Comp Sanction</span></div>
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 12px; height: 12px; border-radius: 3px; background-color: #9f1239;"></div><span style="color: #475569; font-size: 12px; font-weight: 500;">Comp PF Paid (Fully Lost)</span></div>
        </div>
    </div>
    """

    st.markdown(final_html.replace('\n', '').strip(), unsafe_allow_html=True)
    st.divider()



   # --- SECTION 7: REASON FOR POTENTIAL LOSS MATRIX (HTML SAAS CARD) ---
    st.subheader("Reason for Potential Loss (Flight Risk Leads Only)")
    st.markdown("Top reasons tagged by our team for leads that were marked 'Lost', but **actually progressed further with a competitor**.")

    # 1. Safely extract potential losses (Flight Risk)
    bp_pot = lost_bp_df[lost_bp_df['user_max_stage'] > 1].copy() if not lost_bp_df.empty else pd.DataFrame()
    log_pot = lost_log_df[lost_log_df['user_max_stage'] > 2].copy() if not lost_log_df.empty else pd.DataFrame()
    san_pot = lost_san_df[lost_san_df['user_max_stage'] > 3].copy() if not lost_san_df.empty else pd.DataFrame()

    # 🚨 DATA CLEANING FIX: Standardize string casing to group duplicates perfectly
    for df_temp in [bp_pot, log_pot, san_pot]:
        if not df_temp.empty and 'lost_reason' in df_temp.columns:
            df_temp['lost_reason'] = df_temp['lost_reason'].astype(str).str.strip().str.title()

    # 2. Combine them safely to find the true Top 5 reasons across the entire pipeline
    valid_dfs = [df for df in [bp_pot, log_pot, san_pot] if not df.empty and 'lost_reason' in df.columns]
    all_pot = pd.concat(valid_dfs) if valid_dfs else pd.DataFrame()
    
    if all_pot.empty or 'lost_reason' not in all_pot.columns:
        st.info("No flight risk leads found with recorded reasons for this selection.")
    else:
        # Filter out empty/null values that might have been titled to 'Nan'
        all_pot = all_pot[~all_pot['lost_reason'].isin(['Nan', 'None', '', 'Na', 'Null'])]
        top_reasons = all_pot['lost_reason'].value_counts().head(5).index.tolist()
        
        stages_data = [
            ("Lost from Sanction", san_pot),
            ("Lost from Login", log_pot),
            ("Lost from BP", bp_pot)
        ]
        
        # Premium SaaS Color Palette for the 5 reasons + 'Other'
        reason_colors = ["#3b82f6", "#8b5cf6", "#f59e0b", "#10b981", "#ef4444", "#94a3b8"] 
        
        # Build the dynamic HTML rows
        rows_html = ""
        for stage_name, df_pot in stages_data:
            tot = df_pot.shape[0] if not df_pot.empty else 0
            if tot == 0:
                continue
            
            bar_segments_html = ""
            for idx, r in enumerate(top_reasons):
                c = df_pot[df_pot['lost_reason'] == r].shape[0] if ('lost_reason' in df_pot.columns) else 0
                pct = (c / tot) * 100
                if pct > 0:
                    # Smart text hiding: Only show the % text if the bar is wide enough to fit it!
                    text_label = f"{pct:.0f}%" if pct >= 5 else "" 
                    bar_segments_html += f'<div style="width: {pct}%; background-color: {reason_colors[idx]}; display: flex; align-items: center; justify-content: center; color: white; font-size: 11px; font-weight: bold; transition: width 0.3s ease;" title="{r}: {c} Leads ({pct:.1f}%)">{text_label}</div>'
            
            # Handle 'Other' Category
            if 'lost_reason' in df_pot.columns:
                other_c = df_pot[~df_pot['lost_reason'].isin(top_reasons)].shape[0]
            else:
                other_c = 0
            
            other_pct = (other_c / tot) * 100
            if other_pct > 0:
                text_label = f"{other_pct:.0f}%" if other_pct >= 5 else ""
                bar_segments_html += f'<div style="width: {other_pct}%; background-color: {reason_colors[5]}; display: flex; align-items: center; justify-content: center; color: white; font-size: 11px; font-weight: bold; transition: width 0.3s ease;" title="Other: {other_c} Leads ({other_pct:.1f}%)">{text_label}</div>'

            rows_html += f"""
            <div style="margin-bottom: 22px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 8px;">
                    <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-weight: 700; color: #1e293b; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">{stage_name}</span>
                    <span style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; color: #64748b; font-size: 12px; font-weight: 600; background-color: #f1f5f9; padding: 2px 8px; border-radius: 12px;">{tot} Leads</span>
                </div>
                <div style="width: 100%; height: 28px; display: flex; border-radius: 6px; overflow: hidden; background-color: #f8fafc; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);">
                    {bar_segments_html}
                </div>
            </div>
            """

        # Build dynamic flexbox legend
        legend_html = ""
        for idx, r in enumerate(top_reasons):
            legend_html += f'<div style="display: flex; align-items: center; gap: 6px;"><div style="width: 12px; height: 12px; border-radius: 3px; background-color: {reason_colors[idx]};"></div><span style="color: #475569; font-size: 12px; font-weight: 500;">{r}</span></div>'
        
        # Add 'Other' to legend
        legend_html += f'<div style="display: flex; align-items: center; gap: 6px;"><div style="width: 12px; height: 12px; border-radius: 3px; background-color: {reason_colors[5]};"></div><span style="color: #475569; font-size: 12px; font-weight: 500;">Other</span></div>'

        # Wrap it all in the master premium card
        final_html = f"""
        <div style="background: linear-gradient(145deg, #ffffff, #f8fafc); border: 1px solid #e2e8f0; border-radius: 12px; padding: 30px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); margin-top: 15px;">
            <div style="margin-bottom: 25px; border-bottom: 1px solid #f1f5f9; padding-bottom: 15px;">
                <h3 style="margin: 0; color: #0f172a; font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 22px;">🔍</span> Autopsy Breakdown
                </h3>
                <p style="margin: 5px 0 0 0; color: #64748b; font-size: 13px;">Distribution of tagged lost reasons dynamically mapped by funnel stage.</p>
            </div>
            {rows_html}
            <div style="display: flex; flex-wrap: wrap; gap: 15px; margin-top: 30px; padding-top: 15px; border-top: 1px dashed #cbd5e1; justify-content: center;">
                {legend_html}
            </div>
        </div>
        """

        # Flatten string so Streamlit Markdown doesn't trap it in a code block
        st.markdown(final_html.replace('\n', '').strip(), unsafe_allow_html=True)
        
   # --- SECTION 8: REGION-WISE COHORT FUNNEL (HEAT-SHADED SAAS TABLE) ---
    st.divider()
    st.markdown('<div class="section-header"><h2>🌍 8. Region-Wise Cohort Funnel Graphic</h2></div>', unsafe_allow_html=True)
    st.markdown("A pure SaaS-style tabular matrix. Scan volume shares instantly via inline bars, while stage-to-stage volumes and conversions are heat-mapped to highlight bottlenecks.")

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

        # Sort by Shared volume descending and limit to Top 10
        grp = grp.sort_values('Shared', ascending=False).head(10)
        
        # Calculate exact drop-off percentages
        grp['l_pct'] = (grp['Login'] / grp['Shared'] * 100).fillna(0)
        grp['s_pct'] = (grp['Sanction'] / grp['Login'] * 100).fillna(0)
        grp['p_pct'] = (grp['PF'] / grp['Sanction'] * 100).fillna(0)

        max_shared = grp['Shared'].max() if not grp.empty else 1

        # Heat-map Logic Engine for the Cells (Volume + % Pill)
        def get_conversion_cell(pct, raw_count, denominator):
            if denominator == 0 or pd.isna(pct):
                return '<div style="display: flex; align-items: center; justify-content: flex-end; gap: 10px; width: 100%;"><span style="color: #94a3b8; font-size: 14px; font-weight: 600; width: 35px; text-align: right;">-</span><div style="background-color: #f1f5f9; color: #94a3b8; padding: 4px 0; border-radius: 6px; width: 48px; text-align: center; font-size: 12px; font-weight: 600; font-family: ui-monospace, monospace;">-</div></div>'
            
            # Grading thresholds
            if pct >= 50:
                bg, text = "#dcfce3", "#166534" # Green
            elif pct >= 30:
                bg, text = "#ffedd5", "#9a3412" # Amber/Orange
            else:
                bg, text = "#fee2e2", "#991b1b" # Red
                
            return f'<div style="display: flex; align-items: center; justify-content: flex-end; gap: 10px; width: 100%;"><span style="color: #334155; font-size: 14px; font-weight: 700; width: 35px; text-align: right;">{int(raw_count):,}</span><div style="background-color: {bg}; color: {text}; padding: 4px 0; border-radius: 6px; width: 48px; text-align: center; font-size: 12px; font-weight: 700; font-family: ui-monospace, monospace; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);">{pct:.0f}%</div></div>'

        # Build Table Header (Increased flex for data columns to fit the new text)
        html_rows = f"""
        <div style="display: flex; align-items: flex-end; padding-bottom: 12px; border-bottom: 2px solid #e2e8f0; margin-bottom: 10px;">
            <div style="flex: 1.5; color: #64748b; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Region</div>
            <div style="flex: 2; color: #64748b; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Volume Share</div>
            <div style="flex: 1.2; text-align: right; color: #64748b; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">BP ➔ Log</div>
            <div style="flex: 1.2; text-align: right; color: #64748b; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Log ➔ San</div>
            <div style="flex: 1.2; text-align: right; color: #64748b; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">San ➔ PF</div>
        </div>
        """

        # Build Table Rows
        for _, row in grp.iterrows():
            loc = row['location']
            shared_vol = int(row['Shared'])
            bar_width = (shared_vol / max_shared) * 100 if max_shared > 0 else 0
            
            l_cell = get_conversion_cell(row['l_pct'], row['Login'], shared_vol)
            s_cell = get_conversion_cell(row['s_pct'], row['Sanction'], row['Login'])
            p_cell = get_conversion_cell(row['p_pct'], row['PF'], row['Sanction'])

            html_rows += f"""
            <div style="display: flex; align-items: center; padding: 12px 0; border-bottom: 1px dashed #f1f5f9; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#f8fafc'" onmouseout="this.style.backgroundColor='transparent'">
                <div style="flex: 1.5; font-size: 14px; font-weight: 700; color: #1e293b;">{loc}</div>
                
                <div style="flex: 2; display: flex; align-items: center; gap: 12px;">
                    <div style="width: 100%; height: 10px; background-color: #f1f5f9; border-radius: 5px; overflow: hidden;">
                        <div style="width: {bar_width}%; height: 100%; background-color: #6366f1; border-radius: 5px;"></div>
                    </div>
                    <div style="font-size: 13px; color: #64748b; font-weight: 600; width: 40px;">{shared_vol:,}</div>
                </div>
                
                <div style="flex: 1.2; display: flex; justify-content: flex-end;">{l_cell}</div>
                <div style="flex: 1.2; display: flex; justify-content: flex-end;">{s_cell}</div>
                <div style="flex: 1.2; display: flex; justify-content: flex-end;">{p_cell}</div>
            </div>
            """

        # Wrap in Master SaaS Card
        final_html = f"""
        <div style="background: linear-gradient(145deg, #ffffff, #f8fafc); border: 1px solid #e2e8f0; border-radius: 12px; padding: 30px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); margin-top: 15px; margin-bottom: 30px;">
            <div style="margin-bottom: 25px;">
                <h3 style="margin: 0; color: #0f172a; font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 22px;">⚡</span> Regional Heat Matrix
                </h3>
            </div>
            {html_rows}
        </div>
        """

        st.markdown(final_html.replace('\n', '').strip(), unsafe_allow_html=True)
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

        # --- NEW SLEEK UI FOR LOW-VOLUME QUERIES (KPI CARDS) ---
        if len(shared_y_branches) > 0:
            q_cols = st.columns(len(shared_y_branches))
            for i, col in enumerate(q_cols):
                with col:
                    # Dynamically adjust colors if the branch has 0 queries
                    bg_color = "#ffffff" if query_totals[i] > 0 else "#f8fafc"
                    border_color = "#cbd5e1" if query_totals[i] > 0 else "#e2e8f0"
                    title_color = "#0f172a" if query_totals[i] > 0 else "#94a3b8"

                    st.markdown(f"""
                    <div style="background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; padding: 15px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                        <h4 style="color: #475569; margin-bottom: 5px; margin-top: 0px; font-size: 16px;">{shared_y_branches[i]}</h4>
                        <h2 style="color: {title_color}; margin-top: 0px; margin-bottom: 15px; font-size: 28px;">
                            {query_totals[i]} <span style="font-size: 14px; font-weight: normal; color: #64748b;">Queries</span>
                        </h2>
                        <div style="display: flex; justify-content: space-around; font-size: 15px; background-color: #f1f5f9; border-radius: 6px; padding: 5px 0;">
                            <span style="color: #16a34a; font-weight: bold;" title="Resolved">✅ {res_vals[i]}</span>
                            <span style="color: #ef4444; font-weight: bold;" title="Unresolved">⏳ {unres_vals[i]}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No branch data available for queries.")

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
        st.markdown("Where our **Workable** Login leads are sitting (Exclusive vs. Tied vs. Flight Risk).")

        log_exc_vals, log_clog_vals, log_csan_vals, log_workable_totals = [], [], [], []

        for b in log_y_branches:
            b_act = active_log_df[active_log_df['location'] == b] if not active_log_df.empty else pd.DataFrame()
            b_workable = b_act[b_act['user_max_stage'] < 4] if not b_act.empty else pd.DataFrame()
            
            log_workable_totals.append(b_workable.shape[0])
            
            # 1. EXCLUSIVE (Clear Wins): Competitor is at BP or Lost (comp_max_stage < 2)
            log_exc_vals.append(b_workable[b_workable['comp_max_stage'] < 2].shape[0] if not b_workable.empty else 0)
            
            # 2. TIED (Comp Login): Competitor is also at Login (comp_max_stage == 2)
            log_clog_vals.append(b_workable[b_workable['comp_max_stage'] == 2].shape[0] if not b_workable.empty else 0)
            
            # 3. FLIGHT RISK (Comp Sanction+): Competitor is at Sanction or above (comp_max_stage >= 3)
            log_csan_vals.append(b_workable[b_workable['comp_max_stage'] >= 3].shape[0] if not b_workable.empty else 0)

        branch_loss_labels = [f"<b>{b}</b><br>{t} Workable" for b, t in zip(log_y_branches, log_workable_totals)]

        exc_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(log_exc_vals, log_workable_totals)]
        clog_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(log_clog_vals, log_workable_totals)]
        csan_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(log_csan_vals, log_workable_totals)]

        exc_labels = [f"{p:.0f}%" if p > 0 else "" for p in exc_pct_num]
        clog_labels = [f"{p:.0f}%" if p > 0 else "" for p in clog_pct_num]
        csan_labels = [f"{p:.0f}%" if p > 0 else "" for p in csan_pct_num]

        fig_loss_log = go.Figure()
        fig_loss_log.add_trace(go.Bar(name="✅ Exclusive (Safe)", y=branch_loss_labels, x=exc_pct_num, orientation='h', marker_color="#a7f3d0", text=exc_labels, textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="#0f172a")))
        fig_loss_log.add_trace(go.Bar(name="⚠️ Tied / Comp. Login", y=branch_loss_labels, x=clog_pct_num, orientation='h', marker_color="#fed7aa", text=clog_labels, textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="#0f172a")))
        fig_loss_log.add_trace(go.Bar(name="🚨 Tied / Comp. Sanction", y=branch_loss_labels, x=csan_pct_num, orientation='h', marker_color="#9f1239", text=csan_labels, textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")))

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
        # --- ROW 2B: LOSING THE ACTIVE PROSPECTS ---
        st.markdown('<div class="section-header"><h2>💸 Losing The Active Prospects (Branch-wise)</h2></div>', unsafe_allow_html=True)
        st.markdown("Where our **Workable** Sanction leads are sitting. *(Note: Active workable Sanction leads cannot be in 'Comp PF', so the only threat here is a Tie at Sanction)*.")

        san_exc_vals, san_csan_vals, san_workable_totals = [], [], []

        for b in san_y_branches:
            b_act = active_san_df[active_san_df['location'] == b] if not active_san_df.empty else pd.DataFrame()
            b_workable = b_act[b_act['user_max_stage'] < 4] if not b_act.empty else pd.DataFrame()
            
            san_workable_totals.append(b_workable.shape[0])
            
            # 1. EXCLUSIVE (Clear Wins): Competitor is at Login, BP, or Lost (comp_max_stage < 3)
            san_exc_vals.append(b_workable[b_workable['comp_max_stage'] < 3].shape[0] if not b_workable.empty else 0)
            
            # 2. TIED (Comp Sanction): Competitor has matched our speed (comp_max_stage == 3)
            san_csan_vals.append(b_workable[b_workable['comp_max_stage'] == 3].shape[0] if not b_workable.empty else 0)

        branch_loss_labels = [f"<b>{b}</b><br>{t} Workable" for b, t in zip(san_y_branches, san_workable_totals)]

        exc_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(san_exc_vals, san_workable_totals)]
        csan_pct_num = [(v/t)*100 if t > 0 else 0 for v, t in zip(san_csan_vals, san_workable_totals)]

        exc_labels = [f"{p:.0f}%" if p > 0 else "" for p in exc_pct_num]
        csan_labels = [f"{p:.0f}%" if p > 0 else "" for p in csan_pct_num]

        fig_loss_san = go.Figure()
        # Safe Leads (Mint Green)
        fig_loss_san.add_trace(go.Bar(name="✅ Exclusive (Safe)", y=branch_loss_labels, x=exc_pct_num, orientation='h', marker_color="#a7f3d0", text=exc_labels, textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="#0f172a")))
        # Tied Leads (Warning Orange)
        fig_loss_san.add_trace(go.Bar(name="⚠️ Tied / Comp. Sanction", y=branch_loss_labels, x=csan_pct_num, orientation='h', marker_color="#fed7aa", text=csan_labels, textposition="inside", insidetextanchor="middle", textfont=dict(weight="bold", color="#0f172a")))

        fig_loss_san.update_layout(barmode="stack", height=380, margin=dict(t=40, b=20, l=20, r=20), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5), xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]), yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b"), autorange="reversed"))
        
        st.plotly_chart(fig_loss_san, width="stretch")
        
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
