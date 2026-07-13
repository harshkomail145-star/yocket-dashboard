import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import google.generativeai as genai
if "messages" not in st.session_state:
    st.session_state.messages = []

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

# ==========================================
# 2. THE LIVE DATA PIPELINE ENGINE (V6 BUSTER)
# ==========================================
@st.cache_data
def process_lead_engine_v6(file):
    df = pd.read_csv(file)
    
    # CRITICAL FIX: Clean Column Names
    df.columns = df.columns.str.strip().str.lower()
    
    # Standardize Dates (Added Call Data)
    date_cols = ['date_shared', 'login_date', 'sanction_date', 'pf_date', 'last_call_date', 'last_connected_call_date']
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

    # --- AI COMMAND CENTER ---
    st.markdown("### 🧠 AI Command Center")
    gemini_key = st.text_input("Gemini API Key", type="password", help="Enter your Google AI API Key to activate CRO Insights.")
    
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

# ==========================================
# 🎨 MASTER UI ENGINES (GLOBAL SCOPE FOR ALL TABS)
# ==========================================
def build_branch_threat_card(branch_name, b_act, stage_num):
    if b_act.empty: return ""
    tot = b_act.shape[0]
    if tot == 0: return ""
    
    dead_c = b_act[b_act['comp_max_stage'] == 4].shape[0]

    if stage_num == 3: 
        san_c = b_act[b_act['comp_max_stage'] == 3].shape[0] 
        log_c = 0 
        exc_c = b_act[b_act['comp_max_stage'] <= 2].shape[0] 
    elif stage_num == 2: 
        san_c = b_act[b_act['comp_max_stage'] == 3].shape[0]
        log_c = b_act[b_act['comp_max_stage'] == 2].shape[0] 
        exc_c = b_act[b_act['comp_max_stage'] <= 1].shape[0]
    else: 
        san_c = b_act[b_act['comp_max_stage'] == 3].shape[0]
        log_c = b_act[b_act['comp_max_stage'] == 2].shape[0]
        exc_c = b_act[b_act['comp_max_stage'] <= 1].shape[0]

    p_dead, p_san, p_log, p_exc = [(c/tot)*100 for c in [dead_c, san_c, log_c, exc_c]]

    if stage_num == 3:
        metrics_html = f"""
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 18px; font-weight: 800; color: #9f1239; line-height: 1;">{p_dead:.0f}%</div>
                <div style="font-size: 10px; color: #94a3b8; font-weight: 700; text-transform: uppercase; margin-top: 2px;">Dead</div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 18px; font-weight: 800; color: #10b981; line-height: 1;">{p_exc:.0f}%</div>
                <div style="font-size: 10px; color: #94a3b8; font-weight: 700; text-transform: uppercase; margin-top: 2px;">Safe</div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 18px; font-weight: 800; color: #ea580c; line-height: 1;">{p_san:.0f}%</div>
                <div style="font-size: 10px; color: #94a3b8; font-weight: 700; text-transform: uppercase; margin-top: 2px;">C-San</div>
            </div>
        """
        bar_html = f"""<div style="width: {p_dead}%; background-color: #9f1239;"></div><div style="width: {p_exc}%; background-color: #10b981;"></div><div style="width: {p_san}%; background-color: #ea580c;"></div>"""
    else:
        metrics_html = f"""
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 18px; font-weight: 800; color: #9f1239; line-height: 1;">{p_dead:.0f}%</div>
                <div style="font-size: 10px; color: #94a3b8; font-weight: 700; text-transform: uppercase; margin-top: 2px;">Dead</div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 18px; font-weight: 800; color: #10b981; line-height: 1;">{p_exc:.0f}%</div>
                <div style="font-size: 10px; color: #94a3b8; font-weight: 700; text-transform: uppercase; margin-top: 2px;">Safe</div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 18px; font-weight: 800; color: #ca8a04; line-height: 1;">{p_log:.0f}%</div>
                <div style="font-size: 10px; color: #94a3b8; font-weight: 700; text-transform: uppercase; margin-top: 2px;">C-Log</div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 18px; font-weight: 800; color: #ea580c; line-height: 1;">{p_san:.0f}%</div>
                <div style="font-size: 10px; color: #94a3b8; font-weight: 700; text-transform: uppercase; margin-top: 2px;">C-San</div>
            </div>
        """
        bar_html = f"""<div style="width: {p_dead}%; background-color: #9f1239;"></div><div style="width: {p_exc}%; background-color: #10b981;"></div><div style="width: {p_log}%; background-color: #fcd34d;"></div><div style="width: {p_san}%; background-color: #ea580c;"></div>"""

    # 🚨 flex: 2 (Takes up 66% of the row)
    raw_html = f"""
    <div style="flex: 2; background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); display: flex; align-items: center; justify-content: space-between; gap: 20px; font-family: ui-sans-serif, system-ui, sans-serif;">
        <div style="width: 140px; flex-shrink: 0;">
            <div style="font-size: 13px; font-weight: 800; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{branch_name}">{branch_name}</div>
            <div style="font-size: 20px; font-weight: 900; color: #0f172a; line-height: 1; margin-top: 4px;">{tot:,} <span style="font-size: 10px; color: #94a3b8; font-weight: 700;">LEADS</span></div>
        </div>
        <div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center; gap: 12px;">
            <div style="display: flex; justify-content: space-between; gap: 10px;">
                {metrics_html}
            </div>
            <div style="width: 100%; height: 8px; display: flex; border-radius: 4px; overflow: hidden; background: #f1f5f9; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);">
                {bar_html}
            </div>
        </div>
    </div>
    """
    return raw_html.replace('\n', '').strip()

def build_branch_aging_card(branch_name, b_workable, date_col):
    tot = b_workable.shape[0]
    if tot == 0:
        return f'<div style="flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #94a3b8; font-weight: 600;">No Workable Leads</div>'
    
    today = pd.to_datetime('today')
    aging_series = (today - pd.to_datetime(b_workable[date_col], errors='coerce')).dt.days.fillna(0)
    
    b1 = (aging_series <= 3).sum()
    b2 = ((aging_series >= 4) & (aging_series <= 7)).sum()
    b3 = ((aging_series >= 8) & (aging_series <= 14)).sum()
    b4 = (aging_series >= 15).sum()
    
    buckets = [b1, b2, b3, b4]
    max_val = max(buckets) if max(buckets) > 0 else 1
    heights = [(v/max_val)*45 for v in buckets] 
    
    colors = ["#a7f3d0", "#fde68a", "#d97706", "#9f1239"]
    labels = ["0-3d", "4-7d", "8-14d", "15d+"]
    
    bars_html = ""
    for i in range(4):
        val = buckets[i]
        h = max(heights[i], 3)
        bars_html += f"""
        <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
            <span style="font-size: 11px; font-weight: 800; color: #1e293b; margin-bottom: 3px;">{val}</span>
            <div style="width: 100%; height: {h}px; background-color: {colors[i]}; border-radius: 3px 3px 0 0; transition: height 0.4s ease;"></div>
            <span style="font-size: 9px; color: #64748b; margin-top: 3px; font-weight: 600;">{labels[i]}</span>
        </div>
        """
        
    # 🚨 flex: 1 (Takes up 33% of the row)
    raw_html = f"""
    <div style="flex: 1; background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 15px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); font-family: ui-sans-serif, system-ui, sans-serif; display: flex; flex-direction: column; justify-content: space-between;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div style="color: #64748b; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Workable Aging</div>
            <div style="font-size: 16px; font-weight: 900; color: #0f172a; line-height: 1;">{tot:,}</div>
        </div>
        <div style="display: flex; gap: 6px; align-items: flex-end; height: 55px; margin-top: 5px;">
            {bars_html}
        </div>
    </div>
    """
    return raw_html.replace('\n', '').strip()

def build_query_saas_card(branch_name, total_q, res_c, unres_c):
    # 🚨 BULLETPROOF ZERO-DIVISION FIX 🚨
    if total_q == 0:
        return f"""
        <div style="background: #f8fafc; border: 1px solid #f1f5f9; border-radius: 8px; padding: 25px 15px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.02); display: flex; flex-direction: column; justify-content: center; height: 100%;">
            <div style="color: #94a3b8; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; font-family: ui-sans-serif, system-ui, sans-serif;">{branch_name} BLOCKING</div>
            <div style="font-size: 42px; font-weight: 800; color: #cbd5e1; line-height: 1; margin-bottom: 12px; font-family: ui-serif, Georgia, serif;">0</div>
            <div style="color: #94a3b8; font-size: 12px; font-family: ui-serif, Georgia, serif; font-style: italic;">No active queries</div>
        </div>
        """.replace('\n', '').strip()

    res_pct = (res_c / total_q) * 100
    unres_pct = (unres_c / total_q) * 100

    return f"""
    <div style="background: white; border: 1px solid #e5e5ea; border-radius: 8px; padding: 25px 15px 20px 15px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02); display: flex; flex-direction: column; justify-content: space-between; height: 100%;">
        <div>
            <div style="color: #8a8a8e; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 15px; font-family: ui-sans-serif, system-ui, sans-serif; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{branch_name} BLOCKING">{branch_name} BLOCKING</div>
            <div style="font-size: 48px; font-weight: 900; color: #832738; line-height: 1; margin-bottom: 12px; font-family: ui-serif, Georgia, serif;">{unres_c}</div>
            <div style="color: #8a8a8e; font-size: 13px; font-family: ui-serif, Georgia, serif; margin-bottom: 25px;">open / unresolved cases</div>
        </div>
        
        <div style="width: 100%; text-align: left; margin-top: auto;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-family: ui-sans-serif, system-ui, sans-serif; font-size: 10px; color: #64748b; font-weight: 600; text-transform: uppercase;">
                <span style="color: #10b981;">{res_c} Resolved</span>
                <span>{total_q} Total</span>
            </div>
            <div style="width: 100%; height: 6px; background: #f1f5f9; border-radius: 3px; overflow: hidden; display: flex;">
                <div style="width: {res_pct}%; background-color: #10b981;" title="Resolved: {res_c}"></div>
                <div style="width: {unres_pct}%; background-color: #832738;" title="Unresolved: {unres_c}"></div>
            </div>
        </div>
    </div>
    """.replace('\n', '').strip()


def build_engagement_saas_card(df_workable):
    if df_workable.empty: return ""
    tot = df_workable.shape[0]

    # Data Check Fallback
    if 'last_call_date' not in df_workable.columns:
        df_workable['last_call_date'] = pd.NaT
    if 'last_connected_call_date' not in df_workable.columns:
        df_workable['last_connected_call_date'] = pd.NaT

    today = pd.to_datetime('today')

    # 1. Bucket Definitions
    untouched_mask = df_workable['last_call_date'].isna()
    not_conn_mask = df_workable['last_call_date'].notna() & df_workable['last_connected_call_date'].isna()
    conn_mask = df_workable['last_connected_call_date'].notna()

    unt_c = untouched_mask.sum()
    not_c = not_conn_mask.sum()
    con_c = conn_mask.sum()

    p_unt = (unt_c / tot) * 100 if tot else 0
    p_not = (not_c / tot) * 100 if tot else 0
    p_con = (con_c / tot) * 100 if tot else 0

    # 2. LTB (Last Attempt) Logic
    df_not = df_workable[not_conn_mask].copy()
    if not df_not.empty:
        df_not['ltb'] = (today - df_not['last_call_date']).dt.days.fillna(0)
        ltb_buckets = [
            df_not[(df_not['ltb'] >= 0) & (df_not['ltb'] <= 3)].shape[0],
            df_not[(df_not['ltb'] >= 4) & (df_not['ltb'] <= 7)].shape[0],
            df_not[(df_not['ltb'] >= 8) & (df_not['ltb'] <= 14)].shape[0],
            df_not[df_not['ltb'] >= 15].shape[0]
        ]
    else:
        ltb_buckets = [0, 0, 0, 0]

    # 3. LCB (Last Connect) Logic
    df_con = df_workable[conn_mask].copy()
    if not df_con.empty:
        df_con['lcb'] = (today - df_con['last_connected_call_date']).dt.days.fillna(0)
        lcb_buckets = [
            df_con[(df_con['lcb'] >= 0) & (df_con['lcb'] <= 3)].shape[0],
            df_con[(df_con['lcb'] >= 4) & (df_con['lcb'] <= 7)].shape[0],
            df_con[(df_con['lcb'] >= 8) & (df_con['lcb'] <= 14)].shape[0],
            df_con[df_con['lcb'] >= 15].shape[0]
        ]
    else:
        lcb_buckets = [0, 0, 0, 0]

    # 4. Histogram Generation Engine
    colors = ["#a7f3d0", "#fde68a", "#dca573", "#9f1239"]
    labels = ["0-3", "4-7", "8-14", "15+"]

    def make_histogram(buckets, is_ltb=True):
        max_v = max(buckets) if max(buckets) > 0 else 1
        heights = [(v / max_v) * 45 for v in buckets]
        bars = ""
        for i in range(4):
            val = buckets[i]
            h = max(heights[i], 3)
            bars += f"""
            <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
                <div style="width: 90%; height: {h}px; background-color: {colors[i]}; border-radius: 3px 3px 0 0; transition: height 0.4s ease;"></div>
                <span style="font-size: 10px; color: #64748b; margin-top: 4px; font-weight: 600;">{labels[i]}</span>
            </div>
            """
        return bars

    ltb_bars = make_histogram(ltb_buckets, True)
    lcb_bars = make_histogram(lcb_buckets, False)

    # UI Hide Logic (Don't render tiny text inside narrow bars)
    unt_txt = f"{unt_c} never logged" if p_unt > 8 else f"{unt_c}"
    not_txt = f"{not_c} not conn." if p_not > 8 else f"{not_c}"
    con_txt = f"{con_c} connected" if p_con > 8 else f"{con_c}"

    # 5. Assemble HTML
    return f"""
    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 25px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); font-family: ui-sans-serif, system-ui, sans-serif; margin-bottom: 25px;">
        <div style="color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 12px;">WORKABLE BASE • {tot:,}</div>
        
        <div style="display: flex; width: 100%; height: 38px; border-radius: 6px; overflow: hidden; margin-bottom: 20px;">
            <div style="width: {p_unt}%; background-color: #9f1239; color: white; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; white-space: nowrap; overflow: hidden;">{unt_txt}</div>
            <div style="width: {p_not}%; background-color: #d97706; color: white; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; white-space: nowrap; overflow: hidden;">{not_txt}</div>
            <div style="width: {p_con}%; background-color: #4d7c5f; color: white; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; white-space: nowrap; overflow: hidden;">{con_txt}</div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1.5fr 1.5fr; gap: 20px;">
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; border-right: 1px dashed #cbd5e1; padding-right: 15px;">
                <div style="color: #94a3b8; font-size: 11px; font-weight: 500;">(untouched —<br>no recency)</div>
            </div>

            <div style="display: flex; flex-direction: column; align-items: center; border-right: 1px dashed #cbd5e1; padding-right: 15px;">
                <div style="color: #b45309; font-size: 11px; font-weight: 700; margin-bottom: 10px; text-transform: uppercase;">LTB • days since last attempt</div>
                <div style="display: flex; width: 100%; align-items: flex-end; height: 50px;">
                    {ltb_bars}
                </div>
            </div>

            <div style="display: flex; flex-direction: column; align-items: center; padding-left: 5px;">
                <div style="color: #4d7c5f; font-size: 11px; font-weight: 700; margin-bottom: 10px; text-transform: uppercase;">LCB • days since last connect</div>
                <div style="display: flex; width: 100%; align-items: flex-end; height: 50px;">
                    {lcb_bars}
                </div>
            </div>
        </div>
    </div>
    """.replace('\n', '').strip()

def build_branch_engagement_row(branch_name, b_workable):
    tot = b_workable.shape[0]
    if tot == 0: return ""
    
    today = pd.to_datetime('today')
    
    # 1. Bucket Definitions (LOGIC CONFIRMED)
    unt_mask = b_workable['last_call_date'].isna() if 'last_call_date' in b_workable.columns else pd.Series(True, index=b_workable.index)
    
    # LTB = Called but NOT Connected
    not_mask = b_workable['last_call_date'].notna() & b_workable['last_connected_call_date'].isna() if 'last_connected_call_date' in b_workable.columns else pd.Series(False, index=b_workable.index)
    
    # LCB = Successfully Connected
    con_mask = b_workable['last_connected_call_date'].notna() if 'last_connected_call_date' in b_workable.columns else pd.Series(False, index=b_workable.index)

    unt_c, not_c, con_c = unt_mask.sum(), not_mask.sum(), con_mask.sum()
    p_unt, p_not, p_con = [(c/tot)*100 for c in [unt_c, not_c, con_c]]

    # 2. Enlarged LTB/LCB Mini Histograms
    def mini_hist(df_subset, date_col):
        if df_subset.empty or date_col not in df_subset.columns:
            buckets = [0, 0, 0, 0]
        else:
            days = (today - df_subset[date_col]).dt.days.fillna(0)
            buckets = [(days <= 3).sum(), ((days >= 4) & (days <= 7)).sum(), ((days >= 8) & (days <= 14)).sum(), (days >= 15).sum()]
            
        max_v = max(buckets) if max(buckets) > 0 else 1
        colors = ["#a7f3d0", "#fde68a", "#dca573", "#9f1239"]
        
        # Increased gap, width, and height to fill the new 45% space
        html = '<div style="display: flex; gap: 6px; align-items: flex-end; height: 28px;">'
        for i in range(4):
            h = max((buckets[i]/max_v)*28, 3) # Taller bars
            html += f'<div style="width: 20px; height: {h}px; background-color: {colors[i]}; border-radius: 2px 2px 0 0;" title="{buckets[i]} leads"></div>'
        html += '</div>'
        return html

    # Feeding the strict masks into the histograms
    ltb_html = mini_hist(b_workable[not_mask], 'last_call_date')
    lcb_html = mini_hist(b_workable[con_mask], 'last_connected_call_date')

    raw_html = f"""
    <div style="background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); display: flex; align-items: center; justify-content: space-between; gap: 20px; font-family: ui-sans-serif, system-ui, sans-serif;">
        
        <div style="width: 140px; flex-shrink: 0;">
            <div style="font-size: 13px; font-weight: 800; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{branch_name}">{branch_name}</div>
            <div style="font-family: ui-monospace, monospace; font-size: 11px; color: #94a3b8; margin-top: 2px;">{tot:,} Lds</div>
        </div>
        
        <div style="flex: 1.3; padding-right: 25px; border-right: 1px dashed #cbd5e1;">
            <div style="display: flex; justify-content: space-between; font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase; margin-bottom: 6px;">
                <span style="color: #9f1239;">{unt_c} Untouched</span>
                <span style="color: #d97706;">{not_c} Not Conn</span>
                <span style="color: #4d7c5f;">{con_c} Connected</span>
            </div>
            <div style="width: 100%; height: 8px; display: flex; border-radius: 4px; overflow: hidden; background: #f1f5f9; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);">
                <div style="width: {p_unt}%; background-color: #9f1239;" title="{unt_c} Untouched"></div>
                <div style="width: {p_not}%; background-color: #d97706;" title="{not_c} Not Connected"></div>
                <div style="width: {p_con}%; background-color: #4d7c5f;" title="{con_c} Connected"></div>
            </div>
        </div>
        
        <div style="flex: 1; display: flex; justify-content: space-around; align-items: center; padding-left: 10px;">
            <div style="display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 10px; font-weight: 800; color: #b45309; margin-bottom: 6px; letter-spacing: 0.5px;">LTB</span>
                {ltb_html}
            </div>
            <div style="display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 10px; font-weight: 800; color: #4d7c5f; margin-bottom: 6px; letter-spacing: 0.5px;">LCB</span>
                {lcb_html}
            </div>
        </div>
        
    </div>
    """
    return raw_html.replace('\n', '').strip()

@st.cache_data(show_spinner=False)
def generate_executive_insight(data_context, section_title, rubric_context, api_key):
    if not api_key: return ""
    
    genai.configure(api_key=api_key)
    # Using the fast flash model for rapid dashboard reloading
    model = genai.GenerativeModel('gemini-3.1-flash-lite') 
    
    prompt = f"""
    ROLE: Collaborative Principal Data Analyst acting as a strategic business partner for an education loan marketplace.
    DASHBOARD WIDGET: {section_title}
    CORE INTENT: {rubric_context}
    
    PIPELINE DATA OBJECTS:
    {data_context}
    
    INTERNAL VOCABULARY & LINGO (MUST USE):
    - Reps/Agents: Refer to them strictly as "Lender RMs".
    - Stale/Uncalled Leads: Refer to them strictly as "Untouched Leads".
    - Delayed/Blocked Files: Refer to them strictly as "Stuck Files".
    - Competitor Risk: If a lead paid PF to a competitor, it is "Lost to competitor". If it is active but the competitor is at a higher stage, call them "Slipping Files" or leads at "Risk to be lost".
    
    BUSINESS CYCLE CONTEXT (FALL COHORT):
    - Sourcing Volume (BP/Shared): Expected to be consistent year-round. Note trends objectively.
    - Fulfillment Peak: May to August is the harvest season. Sanctions and PF Paid MUST be at peak volume. If we are missing targets here, focus on constructive solutions to catch up.
    - Fulfillment Dead Zone: February to April is historically slower for Sanctions/PF. Factor this in and do not sound false alarms for natural volume drops during these months.
    
    CRITICAL ANALYTICAL GUARDRAILS:
    1. ZERO NUMBER REGURGITATION: Never state 'X increased by Y%' or list the raw metrics from the context. The user is staring directly at the visualization. Interpret what the data *means* operationally.
    2. FUNNEL FRICTION DETECTOR: Look for structural imbalances. If initial stages are outperforming but trailing stages drop below the target, identify the operational handoff failure constructively so the team can fix it.
    3. PATTERN DETECTION: If a specific loss reason dominates or a single region exhibits high leakages to competitors, isolate that specific outlier.
    4. LENGTH & STYLE: Maximum 2 to 3 sentence-style lines. Bullet points are banned. Keep the output flat and continuous.
    5. STYLE FILTER (CRITICAL): Your tone MUST be helpful, supportive, and partnership-driven. Use "we" phrasing (e.g., "We have an opportunity to...", "We can fix this by...", "Let's focus our Lender RMs on..."). Absolutely NO rude, cutthroat, aggressive, or dictatorial language. Be the helpful guide the team relies on.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Operational Analysis Offline: ({str(e)})"
                      
def build_ai_insight_card(insight_text):
    if not insight_text: return ""
    
    raw_html = f"""
    <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid #4f46e5; border-radius: 8px; padding: 18px 25px; margin-top: -25px; margin-bottom: 30px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); font-family: ui-sans-serif, system-ui, sans-serif;">
        <div style="color: #1e293b; font-size: 14px; line-height: 1.6; font-weight: 500;">
            {insight_text}
        </div>
    </div>
    """
    return raw_html.replace('\n', '').strip()

def stream_executive_brief(master_context, time_depth, api_key):
    if not api_key:
        yield "Please enter a valid Gemini API key."
        return
        
    genai.configure(api_key=api_key)
    # 1.5 Pro is better here for deep, long-form synthesis across multiple data points
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    if "2-Minute" in time_depth:
        instructions = """
        Act as a ruthless Risk Manager. Focus STRICTLY on active competitor threats, pipeline leakage, and lost potential. 
        - IGNORE all positive metrics, wins, and healthy cohorts. 
        - Highlight the top 3 immediate risks where we are actively losing money to competitors right now (e.g., specific branches bleeding leads, high 'Not Interested' sales losses, or workable files stuck aging >7 days). 
        - Use three bolded headers. Maximum 250 words.
        """
    elif "5-Minute" in time_depth:
        instructions = """
        Provide a balanced operational review. 
        - Cover the macro YoY trend.
        - Identify the exact bottleneck in the cohort funnel.
        - Call out the top failing branches dragging down conversion. 
        - Use clean Markdown sections. Maximum 650 words.
        """
    else:
        instructions = """
        Execute a comprehensive forensic audit. 
        - Analyze macro trends.
        - Break down the exact conversion velocity friction.
        - Cross-examine the flight risk autopsy against branch leakage.
        - Prescribe strategic fixes for the Lender RMs. 
        - Leave no stone unturned. Maximum 1500 words.
        """

    prompt = f"""
    ROLE: Principal Data Analyst generating an end-to-end operational briefing.
    DEPTH: {instructions}
    
    INTERNAL VOCABULARY TO USE:
    Lender RMs, Untouched Leads, Stuck Files, Bleeding leads, Handoff failure, Historical baseline, Sales Loss (for 'Not Interested' competitor wins).
    
    MASTER DASHBOARD DATA PAYLOAD:
    {master_context}
    
    Synthesize this data. Do not just list the numbers back to me—tell me the story of where we are losing money and how to fix it.
    """
    
    try:
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            yield chunk.text
    except Exception as e:
        yield f"Briefing Generation Offline: ({str(e)})"

# ==========================================
# 4. TAB DECLARATIONS
# ==========================================
tab_overall, tab_bp_login, tab_log_san, tab_san_pf, tab5, tab6 = st.tabs([
    "🌐 Overall Performance", 
    "🔍 BP to Login",
    "📝 Login to Sanction",
    "✅ Sanction to PF",
    "🤖 Executive Briefing",
    "💬 Ask BOS"
])

# ==========================================
# TAB 1: OVERALL PERFORMANCE
# ==========================================
with tab_overall:
    # ==========================================
    # --- COMBINED SECTION 1 & 2: EXECUTIVE YOY MATRIX ---
    # ==========================================
    st.markdown('<div class="section-header"><h2> 1. YoY Executive Performance</h2></div>', unsafe_allow_html=True)
    st.markdown("**Purpose:** Compares our overall lead volume and growth this year directly against the same time last year. This helps us see if we are ahead of or falling behind our historical targets.")

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

    # ==========================================
    # 🧠 GEMINI AI INJECTION: YOY MATRIX
    # ==========================================
    if gemini_key:
        yoy_rubric = """
        Compare current YTD volumes against the identical YTD calendar mask for the previous year. 
        - GOOD PERFORMANCE: 2026 absolute metrics exceed 2025 by >= 5%.
        - FLAG IMPROVEMENT (RATIO DROP): Look at the underlying conversion ratios (e.g., Shared-to-Login ratio). Even if absolute volumes are higher this year, explicitly flag if the *ratio of conversion* was better last year.
        - MUST USE LINGO: Baseline, YTD, Funnel Delta.
        """
        yoy_context = f"""
        Baseline Fall 25 YTD -> Shared: {f25_shr}, Login: {f25_log}, Sanction: {f25_san}, PF Paid: {f25_pf}
        Current Fall 26 YTD -> Shared: {f26_shr}, Login: {f26_log}, Sanction: {f26_san}, PF Paid: {f26_pf}
        Operational Delta -> Shared Delta: {f26_shr - f25_shr}, Login Delta: {f26_log - f25_log}, Sanction Delta: {f26_san - f25_san}, PF Paid Delta: {f26_pf - f25_pf}
        """
        with st.spinner("Auditing YoY Pipeline Health..."):
            yoy_insight = generate_executive_insight(yoy_context, "YoY Performance Matrix", yoy_rubric, gemini_key)
            st.markdown(build_ai_insight_card(yoy_insight), unsafe_allow_html=True)


    # ---------------------------------------------------------
    # PART B: PREMIUM HTML BAR CHART (JAN - AUG)
    # ---------------------------------------------------------
    st.markdown("<h4 style='color: #334155; font-size: 16px; font-weight: 700; margin-top: 35px; margin-bottom: 15px;'>YoY Monthly Login Pacing & Growth</h4>", unsafe_allow_html=True)

    month_nums = [1, 2, 3, 4, 5, 6, 7, 8]
    month_names = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG']

    m_f25_log, m_f26_log = [], []
    for m in month_nums:
        m_f25_log.append(df_master[(df_master['login_date'].dt.month == m) & (df_master['login_date'].dt.year == 2025)].shape[0])
        m_f26_log.append(df_master[(df_master['login_date'].dt.month == m) & (df_master['login_date'].dt.year == 2026)].shape[0])

    # Calculate global max to accurately scale the bar heights mathematically
    global_max = max(max(m_f25_log) if m_f25_log else 0, max(m_f26_log) if m_f26_log else 0)
    if global_max == 0: global_max = 1 # Prevent division by zero

    chart_bars_html = ""
    for i in range(8):
        v25 = m_f25_log[i]
        v26 = m_f26_log[i]
        m_name = month_names[i]

        # Dynamic Growth Pill Logic
        if v25 == 0 and v26 > 0:
            pill_html = "<div style='background:#dcfce3; color:#166534; font-size:11px; padding:3px 8px; border-radius:12px; font-weight:700; margin-bottom: 15px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>+MAX</div>"
        elif v25 == 0 and v26 == 0:
            pill_html = "<div style='background:#f1f5f9; color:#64748b; font-size:11px; padding:3px 8px; border-radius:12px; font-weight:700; margin-bottom: 15px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>-</div>"
        else:
            pct = ((v26 - v25) / v25) * 100
            if pct > 0:
                pill_html = f"<div style='background:#dcfce3; color:#166534; font-size:11px; padding:3px 8px; border-radius:12px; font-weight:700; margin-bottom: 15px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>▲ {pct:.0f}%</div>"
            elif pct < 0:
                pill_html = f"<div style='background:#fee2e2; color:#991b1b; font-size:11px; padding:3px 8px; border-radius:12px; font-weight:700; margin-bottom: 15px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>▼ {abs(pct):.0f}%</div>"
            else:
                pill_html = f"<div style='background:#f1f5f9; color:#64748b; font-size:11px; padding:3px 8px; border-radius:12px; font-weight:700; margin-bottom: 15px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>0%</div>"

        # Math for the Bar Heights (Max height of 180px)
        h25 = max((v25 / global_max) * 180, 4) 
        h26 = max((v26 / global_max) * 180, 4)

        chart_bars_html += f"""
        <div style="display: flex; flex-direction: column; align-items: center; flex: 1; transition: background-color 0.2s; border-radius: 8px; padding-top: 10px;" onmouseover="this.style.backgroundColor='#f8fafc'" onmouseout="this.style.backgroundColor='transparent'">
            {pill_html}
            <div style="display: flex; align-items: flex-end; justify-content: center; gap: 6px; height: 210px; width: 100%;">
                
                <div style="display: flex; flex-direction: column; align-items: center; gap: 5px; width: 35px;" title="Fall 25: {v25:,}">
                    <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 11px; font-weight: 600; color: #94a3b8;">{v25}</span>
                    <div style="width: 100%; height: {h25}px; background-color: #cbd5e1; border-radius: 4px 4px 0 0; transition: height 0.4s ease;"></div>
                </div>
                
                <div style="display: flex; flex-direction: column; align-items: center; gap: 5px; width: 35px;" title="Fall 26: {v26:,}">
                    <span style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 12px; font-weight: 800; color: #2563eb;">{v26}</span>
                    <div style="width: 100%; height: {h26}px; background-color: #3b82f6; border-radius: 4px 4px 0 0; transition: height 0.4s ease; box-shadow: 0 4px 10px rgba(59, 130, 246, 0.25);"></div>
                </div>
                
            </div>
            <div style="margin-top: 15px; font-family: ui-sans-serif, system-ui, sans-serif; font-size: 12px; font-weight: 800; color: #475569; text-transform: uppercase; letter-spacing: 0.5px;">{m_name}</div>
        </div>
        """

    # Wrap the entire chart in a clean SaaS Container
    master_chart_html = f"""
    <div style="background: linear-gradient(145deg, #ffffff, #f8fafc); border: 1px solid #e2e8f0; border-radius: 12px; padding: 30px 20px 20px 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); margin-bottom: 30px;">
        
        <div style="display: flex; justify-content: space-around; align-items: flex-end; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 15px;">
            {chart_bars_html}
        </div>
        
        <div style="display: flex; gap: 20px; justify-content: center; font-family: ui-sans-serif, system-ui, sans-serif; font-size: 12px; color: #64748b; font-weight: 600;">
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 12px; height: 12px; background: #cbd5e1; border-radius: 3px;"></div> Fall 25 Baseline</div>
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width: 12px; height: 12px; background: #3b82f6; border-radius: 3px;"></div> Fall 26 Current</div>
        </div>
    </div>
    """

    # Flatten HTML to bypass Streamlit markdown rendering bugs
    st.markdown(master_chart_html.replace('\n', '').strip(), unsafe_allow_html=True)
    st.divider()

    # --- SECTION 2: M-O-M PROGRESSION (PURE SVG SAAS TRACKER) ---
    st.markdown('<div class="section-header"><h2>2A. 2026 M-o-M Progression of Metrics</h2></div>', unsafe_allow_html=True)
    st.markdown("**Purpose:** Tracks the total number of files at each stage, month by month. It shows us the natural peaks and dips in our business volume throughout the year.")
    
    from datetime import datetime
    current_month = datetime.now().month

    # 🚨 LOGIC PIVOT: Now pulling absolute 2026 calendar volumes from df_master
    def get_absolute_monthly_counts(df, date_col, target_year, target_month):
        if date_col not in df.columns:
            return [0] * target_month
        
        # Filter for the exact calendar year, ignoring the cohort tag completely
        year_data = df[df[date_col].dt.year == target_year][date_col]
        
        counts = year_data.dt.month.value_counts().reindex(range(1, target_month + 1)).fillna(0)
        return counts.tolist()

    shared_mom = get_absolute_monthly_counts(df_master, 'date_shared', 2026, current_month)
    login_mom = get_absolute_monthly_counts(df_master, 'login_date', 2026, current_month)
    sanc_mom = get_absolute_monthly_counts(df_master, 'sanction_date', 2026, current_month)
    pf_mom = get_absolute_monthly_counts(df_master, 'pf_date', 2026, current_month)

    all_months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    months_list = all_months[:len(shared_mom)]

    # --- SVG MAPPING ENGINE ---
    svg_w, svg_h = 800, 250
    max_val = max(shared_mom + login_mom + sanc_mom + pf_mom) if any([shared_mom, login_mom, sanc_mom, pf_mom]) else 1
    
    def get_coords(data):
        pts = []
        if len(data) <= 1: return pts
        for i, val in enumerate(data):
            x = (i / (len(data) - 1)) * (svg_w - 60) + 30
            y = (svg_h - 40) - (val / max_val * (svg_h - 80))
            pts.append((x, y))
        return pts

    def build_svg_line(data, color, offset=0):
        coords = get_coords(data)
        if not coords: return ""
        
        # Mathematical curve smoother
        def get_spline_path(coords):
            if len(coords) < 2: return ""
            if len(coords) == 2: return f"M {coords[0][0]},{coords[0][1]} L {coords[1][0]},{coords[1][1]}"
            path = f"M {coords[0][0]},{coords[0][1]}"
            for i in range(len(coords) - 1):
                x0, y0 = coords[i]
                x1, y1 = coords[i+1]
                cp1x = (x0 + x1) / 2
                path += f" C {cp1x},{y0} {cp1x},{y1} {x1},{y1}"
            return path
            
        path_d = get_spline_path(coords)
        line = f'<path d="{path_d}" fill="none" stroke="{color}" stroke-width="3" />'
        
        # Add Circles and Text Labels
        points = ""
        for x, y in coords:
            points += f'<circle cx="{x}" cy="{y}" r="4" fill="{color}" />'
        
        labels = ""
        for i, val in enumerate(data):
            x, y = coords[i]
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
    if len(months_list) > 1:
        for i, m in enumerate(months_list):
            x = (i / (len(months_list) - 1)) * (svg_w - 60) + 30
            xaxis_labels += f'<text x="{x}" y="{svg_h - 10}" text-anchor="middle" fill="#64748b" font-size="12" font-weight="600">{m}</text>'

    final_card = f"""
    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 25px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
        <svg viewBox="0 0 {svg_w} {svg_h}" style="width: 100%; height: auto; overflow: visible;">
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

    # ==========================================
    # 🧠 GEMINI AI INJECTION: M-O-M PROGRESSION
    # ==========================================
    if gemini_key:
        from datetime import datetime
        current_day = datetime.now().day
        
        # 🚨 DYNAMIC PACING LOGIC 🚨
        # If it's before the 15th, hide the current month from the AI so it doesn't hallucinate a volume crash.
        if current_day < 15 and len(months_list) > 1:
            ai_months = months_list[:-1]
            ai_shared = shared_mom[:-1]
            ai_login = login_mom[:-1]
            ai_sanc = sanc_mom[:-1]
            ai_pf = pf_mom[:-1]
            time_note = "CRITICAL: The current ongoing month has been intentionally hidden from this data because it is less than 15 days old. Base your trends ONLY on the completed months provided."
        else:
            ai_months = months_list
            ai_shared = shared_mom
            ai_login = login_mom
            ai_sanc = sanc_mom
            ai_pf = pf_mom
            time_note = f"CRITICAL: We are currently {current_day} days into the final month listed. Factor in month-to-date pacing before claiming volume is crashing."

        mom_rubric = """
        Evaluate growth patterns based on total monthly absolute volumes at each pipeline phase.
        - GOOD PERFORMANCE: Positive month-over-month trajectory across all stages.
        - FLAG IMPROVEMENT (DIFFERENTIAL DROP): Highlight if one metric drops significantly more than the others in a specific month (e.g., if Logins dropped slightly, but Sanctions dropped massively in April).
        - MUST USE LINGO: Seasonal peaks, Heartbeat, Sourcing volume.
        """
        
        mom_context = f"""
        {time_note}
        Months Tracked: {ai_months}
        Top of Funnel (Shared Leads) Volume: {ai_shared}
        Login Volume: {ai_login}
        Sanction Volume: {ai_sanc}
        PF Paid Volume: {ai_pf}
        """
        
        with st.spinner("Gemini is analyzing M-o-M Momentum..."):
            mom_insight = generate_executive_insight(mom_context, "2026 M-o-M Progression", mom_rubric, gemini_key)
            st.markdown(build_ai_insight_card(mom_insight), unsafe_allow_html=True)
    
    # --- SECTION 2B: IN-MONTH CONVERSION VELOCITY (SVG LINE MATRIX) ---
    st.divider()
    st.markdown('<div class="section-header"><h2>2B. In-Month Conversion Velocity (YoY)</h2></div>', unsafe_allow_html=True)
    st.markdown("**Purpose:** Measures the percentage of leads that successfully move to the next stage within the exact same month. This tells us how fast our pipeline is moving compared to last year.")                                                                             

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

    # ==========================================
    # 🧠 GEMINI AI INJECTION: CONVERSION VELOCITY
    # ==========================================
    if gemini_key:
        velocity_rubric = """
        Compare this year's monthly conversion speed against last year's monthly velocity.
        - GOOD PERFORMANCE: Current year velocity meets or exceeds last year's percentages.
        - FLAG IMPROVEMENT: If last year's in-month velocity was consistently higher, explicitly highlight that the "speed of conversion has decreased" compared to last year.
        - MUST USE LINGO: Pipeline Velocity, Bottleneck zone, Funnel Friction.
        """
        
        # Format the arrays nicely for the AI to read
        v25_bp_log = [f"{v:.1f}%" if pd.notna(v) else "N/A" for v in f25_bp_log]
        v26_bp_log = [f"{v:.1f}%" if pd.notna(v) else "N/A" for v in f26_bp_log]
        v25_log_san = [f"{v:.1f}%" if pd.notna(v) else "N/A" for v in f25_log_san]
        v26_log_san = [f"{v:.1f}%" if pd.notna(v) else "N/A" for v in f26_log_san]
        v25_san_pf = [f"{v:.1f}%" if pd.notna(v) else "N/A" for v in f25_san_pf]
        v26_san_pf = [f"{v:.1f}%" if pd.notna(v) else "N/A" for v in f26_san_pf]
        
        velocity_context = f"""
        Months: {month_names}
        BP to Login -> Fall 25: {v25_bp_log} | Fall 26: {v26_bp_log}
        Login to Sanction -> Fall 25: {v25_log_san} | Fall 26: {v26_log_san}
        Sanction to PF -> Fall 25: {v25_san_pf} | Fall 26: {v26_san_pf}
        """
        with st.spinner("Gemini is auditing Pipeline Velocity against SLAs..."):
            velocity_insight = generate_executive_insight(velocity_context, "In-Month Conversion Velocity (YoY)", velocity_rubric, gemini_key)
            st.markdown(build_ai_insight_card(velocity_insight), unsafe_allow_html=True)

        st.divider()

    # --- SECTION 3: SHARED LEAD COHORT FUNNEL (HIGH-TECH HTML) ---
    st.markdown('<div class="section-header"><h2>3. Fall 26 Shared Leads Cohort</h2></div>', unsafe_allow_html=True)
    st.markdown("**Purpose:** Shows the complete journey of all leads in the Fall '26 group. It highlights exactly how many files are currently active, successfully converted, or lost at each stage.")
    
    # 1. Pipeline Data Calculations
    tot_shared = df_cohort['date_shared'].notnull().sum() if 'date_shared' in df_cohort.columns else 0
    tot_login = df_cohort['login_date'].notnull().sum() if 'login_date' in df_cohort.columns else 0
    tot_sanc = df_cohort['sanction_date'].notnull().sum() if 'sanction_date' in df_cohort.columns else 0
    tot_pf = df_cohort['pf_date'].notnull().sum() if 'pf_date' in df_cohort.columns else 0
    
    curr_bp = df_cohort[df_cohort['lender_stage'] == 'Bank Prospect'].shape[0] if 'lender_stage' in df_cohort.columns else 0
    curr_log = df_cohort[df_cohort['lender_stage'] == 'Login'].shape[0] if 'lender_stage' in df_cohort.columns else 0
    curr_san = df_cohort[df_cohort['lender_stage'] == 'Sanction'].shape[0] if 'lender_stage' in df_cohort.columns else 0

    if 'lost_category' in df_cohort.columns:
        lost_bp_funnel = df_cohort[df_cohort['lost_category'].astype(str).str.contains('BP', case=False, na=False)].shape[0]
        lost_log_funnel = df_cohort[df_cohort['lost_category'].astype(str).str.contains('Login', case=False, na=False)].shape[0]
        lost_san_funnel = df_cohort[df_cohort['lost_category'].astype(str).str.contains('Sanction', case=False, na=False)].shape[0]
    else:
        lost_bp_funnel, lost_log_funnel, lost_san_funnel = 0, 0, 0

    bp_log_pct = (tot_login/tot_shared)*100 if tot_shared > 0 else 0
    log_san_pct = (tot_sanc/tot_login)*100 if tot_login > 0 else 0
    san_pf_pct = (tot_pf/tot_sanc)*100 if tot_sanc > 0 else 0
    
    # 2. Master HTML Card Builders (Decreasing box heights for true funnel effect)
    def build_funnel_block(title, total, active, lost, color, size_tier, show_breakdown=True):
        # Added 'height' to dynamically shrink the cards step-by-step
        sizes = {
            1: {"flex": "3", "pad": "20px", "title": "16px", "num": "42px", "b_pad": "4px 10px", "b_num": "14px", "b_txt": "9px", "height": "180px"},
            2: {"flex": "2.5", "pad": "16px", "title": "15px", "num": "36px", "b_pad": "4px 8px", "b_num": "13px", "b_txt": "8px", "height": "155px"},
            3: {"flex": "2", "pad": "14px", "title": "14px", "num": "30px", "b_pad": "3px 6px", "b_num": "12px", "b_txt": "8px", "height": "135px"},
            4: {"flex": "1.5", "pad": "12px", "title": "13px", "num": "26px", "b_pad": "0", "b_num": "0", "b_txt": "0", "height": "100px"}
        }
        s = sizes[size_tier]

        # Pins Active to the bottom-left and Lost to the bottom-right
        breakdown_html = f"""
        <div style="display: flex; justify-content: space-between; width: 100%; margin-top: auto; padding-top: 15px;">
            <div style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.2); color: #166534; padding: {s['b_pad']}; border-radius: 4px; text-align: center; line-height: 1.1;">
                <div style="font-size: {s['b_num']}; font-weight: 900; font-family: ui-monospace, monospace;">{active:,}</div>
                <div style="font-size: {s['b_txt']}; font-weight: 800; text-transform: uppercase; opacity: 0.8;">Active</div>
            </div>
            <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); color: #991b1b; padding: {s['b_pad']}; border-radius: 4px; text-align: center; line-height: 1.1;">
                <div style="font-size: {s['b_num']}; font-weight: 900; font-family: ui-monospace, monospace;">{lost:,}</div>
                <div style="font-size: {s['b_txt']}; font-weight: 800; text-transform: uppercase; opacity: 0.8;">Lost</div>
            </div>
        </div>
        """ if show_breakdown else ""
        
        # Swapped hardcoded min-height for the dynamic s['height']
        return f"""
        <div style="flex: {s['flex']}; background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%); border: 1px solid #e2e8f0; border-top: 4px solid {color}; border-radius: 12px; padding: {s['pad']}; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02); transition: transform 0.2s, box-shadow 0.2s; display: flex; flex-direction: column; align-items: center; min-height: {s['height']};" onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 12px 20px -5px rgba(0,0,0,0.1)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px -1px rgba(0,0,0,0.02)'">
            <div style="font-size: {s['title']}; font-weight: 800; color: #64748b; text-transform: uppercase; letter-spacing: 1px; font-family: ui-sans-serif, system-ui, sans-serif; text-align: center; width: 100%;">
                {title}
            </div>
            <div style="font-size: {s['num']}; font-weight: 900; color: #0f172a; margin: 8px 0 0 0; line-height: 1; font-family: ui-sans-serif, system-ui, sans-serif; letter-spacing: -1px; text-align: center;">{total:,}</div>
            {breakdown_html}
        </div>
        """

    def build_funnel_arrow(pct, size_tier):
        arrow_sizes = {
            1: {"text": "14px", "arrow": "28px", "pad": "6px 14px"},
            2: {"text": "13px", "arrow": "24px", "pad": "5px 12px"},
            3: {"text": "12px", "arrow": "20px", "pad": "4px 10px"}
        }
        s = arrow_sizes[size_tier]
        return f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; min-width: 60px; z-index: 10;">
            <div style="background: linear-gradient(135deg, #eff6ff, #dbeafe); border: 1px solid #bfdbfe; color: #1d4ed8; font-size: {s['text']}; font-weight: 900; padding: {s['pad']}; border-radius: 20px; box-shadow: inset 0 1px 2px rgba(255,255,255,0.7), 0 2px 4px rgba(0,0,0,0.05); font-family: ui-monospace, monospace; white-space: nowrap;">
                {pct:.1f}%
            </div>
            <div style="color: #cbd5e1; font-size: {s['arrow']}; font-weight: 900; margin-top: 0px; line-height: 1.2; filter: drop-shadow(0px 2px 2px rgba(0,0,0,0.05));">➔</div>
        </div>
        """

    # 3. Assemble the Master Flexbox Grid
    html_funnel = f"""
    <div style="background: linear-gradient(145deg, #ffffff, #f1f5f9); border: 1px solid #e2e8f0; border-radius: 16px; padding: 35px 25px; box-shadow: inset 0 2px 4px rgba(255,255,255,0.8), 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 25px; overflow-x: auto;">
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px; min-width: 850px;">
            {build_funnel_block('Shared', tot_shared, curr_bp, lost_bp_funnel, '#4f46e5', 1)}
            {build_funnel_arrow(bp_log_pct, 1)}
            {build_funnel_block('Login', tot_login, curr_log, lost_log_funnel, '#3b82f6', 2)}
            {build_funnel_arrow(log_san_pct, 2)}
            {build_funnel_block('Sanction', tot_sanc, curr_san, lost_san_funnel, '#f59e0b', 3)}
            {build_funnel_arrow(san_pf_pct, 3)}
            {build_funnel_block('PF Paid', tot_pf, tot_pf, 0, '#10b981', 4, show_breakdown=False)}
        </div>
    </div>
    """
    
    st.markdown(html_funnel.replace('\n', '').strip(), unsafe_allow_html=True)


    # ==========================================
    # 🧠 GEMINI AI INJECTION: FALL 26 COHORT
    # ==========================================
    if gemini_key:
        cohort_rubric = """
        Evaluate the end-to-end cohort journey through all four milestones against our expected operational health.
        - HISTORICAL BASELINES: A healthy funnel expects BP to Login > 70%, Login to Sanction > 50%, and Sanction to PF > 50%.
        - GOOD PERFORMANCE: Conversion rates are tracking at or above historical norms.
        - FLAG IMPROVEMENT: Identify exactly which stage is trailing the baseline. Frame it operationally (e.g., "experiencing friction" or "underperforming the standard run-rate").
        - BANNED WORDS: Absolutely do NOT use the words "target", "quota", or "KPI" in your output.
        - MUST USE LINGO: Fall Cohort, Bleeding leads, Handoff failure, Historical baseline.
        """
        cohort_context = f"""
        Total Shared: {tot_shared:,}
        Total Login: {tot_login:,} (Current Conversion: {bp_log_pct:.1f}%)
        Total Sanction: {tot_sanc:,} (Current Conversion: {log_san_pct:.1f}%)
        Total PF Paid: {tot_pf:,} (Current Conversion: {san_pf_pct:.1f}%)
        """
        with st.spinner("Gemini is auditing Funnel Conversion Health..."):
            cohort_insight = generate_executive_insight(cohort_context, "Shared Leads Pipeline (Fall 26 Cohort)", cohort_rubric, gemini_key)
            st.markdown(build_ai_insight_card(cohort_insight), unsafe_allow_html=True)



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
    st.markdown('<div class="section-header"><h2>4. Active Pipeline Health & Competitor Risk</h2></div>', unsafe_allow_html=True)
    st.markdown("**Purpose:** Evaluates the files currently being worked on by our team. It highlights how old the files are getting and flags if a competitor is moving faster than us on a shared lead.")

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
    
    # ==========================================
    # 🚨 THE NEW ENGAGEMENT TRACKER INJECTION 🚨
    # ==========================================
    st.markdown("<h4 style='color: #334155; font-size: 16px; font-weight: 700; margin-top: 35px; margin-bottom: 10px;'>Calling Engagement & Recency (All Workable Leads)</h4>", unsafe_allow_html=True)
    st.markdown("Measuring the interaction velocity of the **Workable Base**. <span style='color:#b45309; font-weight:bold;'>LTB</span> (Days since last call attempt) vs. <span style='color:#4d7c5f; font-weight:bold;'>LCB</span> (Days since last successful connect).", unsafe_allow_html=True)
    
    # Safely aggregate all workable leads from all 3 stages
    valid_workables = [df for df in [work_bp, work_log, work_san] if not df.empty]
    overall_workable_df = pd.concat(valid_workables) if valid_workables else pd.DataFrame()
    
    engagement_html = build_engagement_saas_card(overall_workable_df)
    st.markdown(engagement_html, unsafe_allow_html=True)
    
    st.divider()

    # ==========================================
    # 🧠 GEMINI AI INJECTION: ACTIVE THREAT MATRIX
    # ==========================================
    if gemini_key:
        # --- THE MISSING CALCULATIONS ---
        bp_safe = active_bp[active_bp['comp_max_stage'] <= 1].shape[0] if not active_bp.empty else 0
        bp_dead = active_bp[active_bp['comp_max_stage'] == 4].shape[0] if not active_bp.empty else 0
        
        log_safe = active_log[active_log['comp_max_stage'] <= 1].shape[0] if not active_log.empty else 0
        log_dead = active_log[active_log['comp_max_stage'] == 4].shape[0] if not active_log.empty else 0
        
        san_safe = active_san[active_san['comp_max_stage'] <= 2].shape[0] if not active_san.empty else 0
        san_dead = active_san[active_san['comp_max_stage'] == 4].shape[0] if not active_san.empty else 0
        
        # Pull calling parameters from overall workable base calculated in your engine
        tot_workable = overall_workable_df.shape[0] if not overall_workable_df.empty else 0
        untouched = overall_workable_df['last_call_date'].isna().sum() if not overall_workable_df.empty else 0

        threat_rubric = """
        Audit active pipeline health based on competitor standing, workable aging, and RM calling input.
        - COMPETITOR STANDING: Flag any stage where Exclusive Leads are < 50%. Warn the business that we are losing the majority of our active leads to competitors at this stage.
        - WORKABLE AGING: Flag if the majority of workable leads in any stage are sitting in the >7 days buckets (8-14d or 15d+). Emphasize that delayed decision-making causes files to slip to competitors.
        - CALLING INPUT: Flag if there is a high volume or majority of "Untouched Leads" that have not been called yet.
        - MUST USE LINGO: Exclusive Leads, Slipping Files, Dead to competitor, Workable base, Aging buckets, Stuck files, Lender RMs, Untouched Leads, Interaction velocity.
        """
        
        threat_context = f"""
        Active Pipeline Summary:
        - BP Stage: Total={active_bp.shape[0]}, Exclusive/Safe={bp_safe}, Dead to Competitor={bp_dead}
        - Login Stage: Total={active_log.shape[0]}, Exclusive/Safe={log_safe}, Dead to Competitor={log_dead}
        - Sanction Stage: Total={active_san.shape[0]}, Exclusive/Safe={san_safe}, Dead to Competitor={san_dead}
        Workable Base Engagement:
        - Total Workable Files: {tot_workable}
        - Untouched Leads (Zero Calls Logged): {untouched} ({(untouched/tot_workable*100) if tot_workable else 0:.1f}%)
        - Stage Aging Buckets (BP/Login/Sanction 15d+): {bp_buckets[3]} / {log_buckets[3]} / {san_buckets[3]} leads
        """
        with st.spinner("Auditing Operational Levers and Flight Risks..."):
            threat_insight = generate_executive_insight(threat_context, "Active Pipeline Health & Competitor Risk", threat_rubric, gemini_key)
            st.markdown(build_ai_insight_card(threat_insight), unsafe_allow_html=True)
    
    # --- SECTION 6: LOST POTENTIAL ANALYSIS (HTML SAAS CARD) ---
    st.divider()
    st.markdown('<div class="section-header"><h2>5. Lost Leads and its Potential</h2></div>', unsafe_allow_html=True)
    st.markdown("**Purpose:** Analyzes the files the Lender marked as 'Lost' to see if they actually moved ahead from that stage with a competitor. This helps us understand leads with the potential that were marked as lost.")
    
    # Data Calculations (Reordered: BP -> Login -> Sanction)
    stages_names = ["Lost from BP", "Lost from Login", "Lost from Sanction"]
    bar_totals = [lost_bp_df.shape[0], lost_log_df.shape[0], lost_san_df.shape[0]]

    true_dead = [
        lost_bp_df[lost_bp_df['user_max_stage'] == 1].shape[0] if not lost_bp_df.empty else 0,
        lost_log_df[lost_log_df['user_max_stage'] <= 2].shape[0] if not lost_log_df.empty else 0,
        lost_san_df[lost_san_df['user_max_stage'] <= 3].shape[0] if not lost_san_df.empty else 0
    ]
    comp_login = [
        lost_bp_df[lost_bp_df['user_max_stage'] == 2].shape[0] if not lost_bp_df.empty else 0,
        0, 
        0
    ]
    comp_sanc = [
        lost_bp_df[lost_bp_df['user_max_stage'] == 3].shape[0] if not lost_bp_df.empty else 0,
        lost_log_df[lost_log_df['user_max_stage'] == 3].shape[0] if not lost_log_df.empty else 0,
        0
    ]
    comp_pf = [
        lost_bp_df[lost_bp_df['user_max_stage'] == 4].shape[0] if not lost_bp_df.empty else 0,
        lost_log_df[lost_log_df['user_max_stage'] == 4].shape[0] if not lost_log_df.empty else 0,
        lost_san_df[lost_san_df['user_max_stage'] == 4].shape[0] if not lost_san_df.empty else 0
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
        
        # Reordered Data Set (BP -> Login -> Sanction)
        stages_data = [
            ("Lost from BP", bp_pot),
            ("Lost from Login", log_pot),
            ("Lost from Sanction", san_pot)
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

    # ==========================================
    # 🧠 GEMINI AI INJECTION: LOST FILE ANALYSIS
    # ==========================================
    if gemini_key:
        lost_rubric = """
        Analyze disposition behavior by mapping potential losses to RM-tagged loss reasons.
        - STEP 1 (IDENTIFY LEAKAGE): Identify exactly which stage (BP, Login, or Sanction) has the highest percentage of "Lost Potential" (leads that progressed with a competitor after being marked lost by us).
        - STEP 2 (AUTOPSY): Immediately cross-reference that specific stage with the top recorded loss reasons provided by the RMs. 
        - STEP 3 (EVALUATE): Evaluate if the RM's stated reason makes logical sense, or if it contradicts the market reality that a competitor successfully closed the file.
        - MUST USE LINGO: Potential Losses, False Dead, Disposition behavior, Autopsy Breakdown, Flight Risk Leads, Market reality.
        """
        
        # Fixed indices to match the new BP -> Login -> Sanction array order
        lost_context = f"""
        Pipeline Leakage Audit:
        - Lost from BP: Total={bar_totals[0]}, Went to Competitor Login/Sanction/PF={comp_login[0] + comp_sanc[0] + comp_pf[0]}
        - Lost from Login: Total={bar_totals[1]}, Went to Competitor Sanction/PF={comp_sanc[1] + comp_pf[1]}
        - Lost from Sanction: Total={bar_totals[2]}, Went to Competitor PF={comp_pf[2]}
        Top Tagged Loss Reasons for Flight Risk Leads: {top_reasons if 'top_reasons' in locals() else 'Check Autopsy Bar Chart'}
        """
        with st.spinner("Auditing Disposition Integrity..."):
            lost_insight = generate_executive_insight(lost_context, "Lost Leads and its Potential", lost_rubric, gemini_key)
            st.markdown(build_ai_insight_card(lost_insight), unsafe_allow_html=True)
        
   # --- SECTION 8: REGION-WISE COHORT FUNNEL (HEAT-SHADED SAAS TABLE) ---
    st.divider()
    st.markdown('<div class="section-header"><h2>6. Region-Wise Cohort Funnel</h2></div>', unsafe_allow_html=True)
    st.markdown("**Purpose:** Breaks down our conversion success rate by specific geographic regions. This pinpoints exactly which local areas are performing well and which ones need more support.")
    
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
    # 🧠 GEMINI AI INJECTION: REGIONAL FUNNEL
    # ==========================================
    if gemini_key:
        regional_rubric = """
        Perform a geographic performance audit comparing regional conversion percentages against the overall lender cohort averages.
        - GOOD PERFORMANCE: Regional conversion rates meet or exceed the overall cohort average for that stage.
        - FLAG IMPROVEMENT: Explicitly flag specific locations where the conversion percentage (BP to Login, Login to Sanction, or Sanction to PF) is notably LOWER than the overall cohort conversion rate.
        - MUST USE LINGO: Regional Heat Matrix, Hub performance, Territory audit.
        """
        
        # Build a text table of the top regions for the AI to read
        regional_data_str = ""
        if not region_df.empty and 'grp' in locals():
            for _, r in grp.iterrows():
                regional_data_str += f"- {r['location']}: BP->Log {r['l_pct']:.1f}%, Log->San {r['s_pct']:.1f}%, San->PF {r['p_pct']:.1f}%\n"

        regional_context = f"""
        Overall Lender Cohort Averages:
        - BP to Login: {bp_log_pct:.1f}%
        - Login to Sanction: {log_san_pct:.1f}%
        - Sanction to PF: {san_pf_pct:.1f}%
        
        Top Regional Performance:
        {regional_data_str}
        """
        with st.spinner("Gemini is running regional performance audit..."):
            regional_insight = generate_executive_insight(regional_context, "Region-Wise Cohort Funnel", regional_rubric, gemini_key)
            st.markdown(build_ai_insight_card(regional_insight), unsafe_allow_html=True)
    
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
        # ==========================================
        # 🧠 GEMINI AI INJECTION: BRANCH PERFORMANCE
        # ==========================================
        if gemini_key:
            branch_perf_rubric = """
            Audit branch-level performance strictly against the overall Lender Average.
            - GOOD PERFORMANCE: Branch conversion is higher than average and TAT is lower than average.
            - FLAG IMPROVEMENT: Identify any branch with a lower conversion rate than the Lender Average. Also, flag branches with a higher TAT than the Lender Average.
            - MAJOR DOUBLE FLAG: Explicitly call out any branch that is failing on BOTH fronts (lower conversion AND higher TAT).
            - MUST USE LINGO: Lender Average, Double Flag, Processing Speed.
            """
            branch_perf_context = f"""
            Stage: BP to Login
            Lender Average Conversion: {lender_avg_conv}% | Lender Average TAT: {lender_avg_tat} days
            Branches Tracked: {shared_y_branches}
            Branch Conversion Rates: {conv_rates}
            Branch TAT (Days): {tat_days}
            """
            with st.spinner("Auditing Branch Performance..."):
                branch_insight = generate_executive_insight(branch_perf_context, "Branch Performance Matrix", branch_perf_rubric, gemini_key)
                st.markdown(build_ai_insight_card(branch_insight), unsafe_allow_html=True)
        st.divider()

        # --- ROW 2 & 3: PIPELINE HEALTH & ENGAGEMENT ---
        st.markdown('<div class="section-header"><h2>⏱️ 2. Active Pipeline Health & Competitor Risk</h2></div>', unsafe_allow_html=True)
        
        threat_aging_html = ""
        engagement_html = ""
        
        for b in shared_y_branches:
            b_act = active_bp_df[active_bp_df['location'] == b] if not active_bp_df.empty else pd.DataFrame()
            if not b_act.empty:
                b_workable = b_act[b_act['comp_max_stage'] < 4]
                
                threat_card = build_branch_threat_card(b, b_act, 1)
                aging_card = build_branch_aging_card(b, b_workable, 'date_shared')
                engage_row = build_branch_engagement_row(b, b_workable)
                
                # 1. Build the 60/40 Split Row
                split_row = f"""
                <div style="display: flex; gap: 15px; align-items: stretch; margin-bottom: 15px;">
                    {threat_card}
                    {aging_card}
                </div>
                """
                threat_aging_html += split_row.replace('\n', '').strip()
                
                # 2. Build the Stacked Engagement Row
                engage_wrapper = f'<div style="margin-bottom: 10px;">{engage_row}</div>'
                engagement_html += engage_wrapper.replace('\n', '').strip()
                
        # Render Section A: The 60/40 Split
        st.markdown("<h4 style='color: #334155; font-size: 15px; font-weight: 700; margin-bottom: 15px; margin-top: 10px;'>A. Competitor Threat & Workable Aging</h4>", unsafe_allow_html=True)
        st.markdown(f'<div style="display: flex; flex-direction: column; margin-bottom: 35px;">{threat_aging_html}</div>', unsafe_allow_html=True)
        
        # Render Section B: The LTB/LCB Stack
        st.markdown("<h4 style='color: #334155; font-size: 15px; font-weight: 700; margin-bottom: 15px;'>B. Calling Engagement & Recency (LTB/LCB)</h4>", unsafe_allow_html=True)
        st.markdown(f'<div style="display: flex; flex-direction: column; margin-bottom: 25px;">{engagement_html}</div>', unsafe_allow_html=True)

        # ==========================================
        # 🧠 GEMINI AI INJECTION: ACTIVE HEALTH & CALLING (2A & 2B)
        # ==========================================
        if gemini_key:
            health_rubric = """
            Audit active pipeline health focusing on competitor threat, workable aging, and RM calling input across branches.
            - COMPETITOR THREAT & AGING (2A): Flag any branch with a low proportion of Safe Leads or where workable files are stuck aging >7 days. Emphasize that delayed decision-making causes files to slip to competitors.
            - CALLING ENGAGEMENT (2B): Flag branches that have poor Calling Input (high untouched leads or LTB/LCB aging in older buckets). Emphasize the need for disposition discipline.
            - MUST USE LINGO: Exclusive/Safe Leads, Competitor Risk, Stuck Files, Untouched leads, Calling input, Disposition discipline, Recency.
            """
            
            # Dynamically extract 2A & 2B stats for the AI
            branch_health_stats = ""
            for i, b in enumerate(shared_y_branches):
                b_act = active_bp_df[active_bp_df['location'] == b]
                b_work = b_act[b_act['comp_max_stage'] < 4] if not b_act.empty else pd.DataFrame()
                safe_c = b_act[b_act['comp_max_stage'] <= 1].shape[0] if not b_act.empty else 0
                untouched_c = b_work['last_call_date'].isna().sum() if not b_work.empty and 'last_call_date' in b_work.columns else 0
                branch_health_stats += f"- {b}: {b_act.shape[0]} Active | {safe_c} Safe | {bp_o7_vals[i]} Stuck (>7d) | {untouched_c} Untouched\n"
            
            health_context = f"""
            Stage: BP Active Pipeline
            Branch-Level Health Metrics:
            {branch_health_stats}
            """
            with st.spinner("Auditing Active Threats and Calling Discipline..."):
                health_insight = generate_executive_insight(health_context, "Active Pipeline Health & Calling Engagement", health_rubric, gemini_key)
                st.markdown(build_ai_insight_card(health_insight), unsafe_allow_html=True)
        
        st.divider()
        
        # --- ROW 4: QUERY RESOLUTION STATUS (SAAS GRID) ---
        st.markdown('<div class="section-header"><h2>❓ 3. Query Resolution Status (Workable BP Leads)</h2></div>', unsafe_allow_html=True)
        st.markdown("Tracking unresolved bottlenecks vs. resolved queries for **Active Workable** BP leads.")

        res_vals, unres_vals, query_totals = [], [], []

        for b in shared_y_branches:
            b_act = active_bp_df[active_bp_df['location'] == b] if not active_bp_df.empty else pd.DataFrame()
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

        query_cards_html = ""
        for i, b in enumerate(shared_y_branches):
            query_cards_html += build_query_saas_card(b, query_totals[i], res_vals[i], unres_vals[i])

        st.markdown(f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 25px;">{query_cards_html}</div>', unsafe_allow_html=True)
        # ==========================================
        # 🧠 GEMINI AI INJECTION: QUERY BOTTLENECKS
        # ==========================================
        if gemini_key:
            query_rubric = """
            Identify operational bottlenecks caused by unresolved queries at the branch level.
            - GOOD PERFORMANCE: All branches have zero unresolved queries.
            - FLAG IMPROVEMENT: Identify any branch carrying unresolved queries. 
            - FORMAT: Keep this insight to a sharp, direct one-liner.
            - MUST USE LINGO: Unresolved queries, Pipeline blockers.
            """
            query_context = f"""
            Branches Tracked: {shared_y_branches}
            Total Queries Logged by Branch: {query_totals}
            Resolved Queries: {res_vals}
            Unresolved Queries (Blocking): {unres_vals}
            """
            with st.spinner("Auditing Query Bottlenecks..."):
                query_insight = generate_executive_insight(query_context, "Query Resolution Status", query_rubric, gemini_key)
                st.markdown(build_ai_insight_card(query_insight), unsafe_allow_html=True)
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
        # ==========================================
        # 🧠 GEMINI AI INJECTION: BRANCH LEAKAGE & AUTOPSY
        # ==========================================
        if gemini_key:
            branch_lost_rubric = """
            Analyze branch-level lost potential and the validity of RM loss reasons.
            - STEP 1 (LOST POTENTIAL): Identify which specific branch has the highest "Lost Potential" percentage. Point out that leads distributed to this branch are being abandoned but successfully processed elsewhere.
            - STEP 2 (AUTOPSY/NOT INTERESTED): Cross-reference the loss reasons. If "Not Interested" is a top reason, explicitly flag this as a "Sales Loss". Emphasize that the lead was clearly interested in a loan, as they went and processed it with another bank.
            - MUST USE LINGO: Lost Potential, Sales Loss, Disposition integrity.
            """
            branch_lost_context = f"""
            Branches Tracked: {shared_y_branches}
            Total Lost Leads by Branch: {lost_branch_totals}
            Lost Potential Percentages by Branch: {potential_loss_pcts}
            Overall Top Flight Risk Reasons: {top_reasons if 'top_reasons' in locals() else 'None recorded'}
            """
            with st.spinner("Auditing Branch-Level Leakage..."):
                branch_lost_insight = generate_executive_insight(branch_lost_context, "Lost Potential & Flight Risk Autopsy", branch_lost_rubric, gemini_key)
                st.markdown(build_ai_insight_card(branch_lost_insight), unsafe_allow_html=True)
            
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
        # ==========================================
        # 🧠 GEMINI AI INJECTION: BRANCH PERFORMANCE
        # ==========================================
        if gemini_key:
            branch_perf_rubric = """
            Audit branch-level performance strictly against the overall Lender Average.
            - GOOD PERFORMANCE: Branch conversion is higher than average and TAT is lower than average.
            - FLAG IMPROVEMENT: Identify any branch with a lower conversion rate than the Lender Average. Also, flag branches with a higher TAT than the Lender Average.
            - MAJOR DOUBLE FLAG: Explicitly call out any branch that is failing on BOTH fronts (lower conversion AND higher TAT).
            - MUST USE LINGO: Lender Average, Double Flag, Processing Speed.
            """
            branch_perf_context = f"""
            Stage: Login to Sanction
            Lender Average Conversion: {lender_avg_conv}% | Lender Average TAT: {lender_avg_tat} days
            Branches Tracked: {log_y_branches}
            Branch Conversion Rates: {conv_rates}
            Branch TAT (Days): {tat_days}
            """
            with st.spinner("Auditing Branch Performance..."):
                branch_insight = generate_executive_insight(branch_perf_context, "Branch Performance Matrix", branch_perf_rubric, gemini_key)
                st.markdown(build_ai_insight_card(branch_insight), unsafe_allow_html=True)

        st.divider()

        # --- ROW 2 & 3: PIPELINE HEALTH & ENGAGEMENT ---
        st.markdown('<div class="section-header"><h2>⏱️ 2. Active Pipeline Health & Competitor Risk</h2></div>', unsafe_allow_html=True)
        
        threat_aging_html = ""
        engagement_html = ""
        
        for b in log_y_branches:
            b_act = active_log_df[active_log_df['location'] == b] if not active_log_df.empty else pd.DataFrame()
            if not b_act.empty:
                b_workable = b_act[b_act['comp_max_stage'] < 4]
                
                threat_card = build_branch_threat_card(b, b_act, 2)
                aging_card = build_branch_aging_card(b, b_workable, 'login_date')
                engage_row = build_branch_engagement_row(b, b_workable)
                
                split_row = f"""
                <div style="display: flex; gap: 15px; align-items: stretch; margin-bottom: 15px;">
                    {threat_card}
                    {aging_card}
                </div>
                """
                threat_aging_html += split_row.replace('\n', '').strip()
                
                engage_wrapper = f'<div style="margin-bottom: 10px;">{engage_row}</div>'
                engagement_html += engage_wrapper.replace('\n', '').strip()
                
        st.markdown("<h4 style='color: #334155; font-size: 15px; font-weight: 700; margin-bottom: 15px; margin-top: 10px;'>A. Competitor Threat & Workable Aging</h4>", unsafe_allow_html=True)
        st.markdown(f'<div style="display: flex; flex-direction: column; margin-bottom: 35px;">{threat_aging_html}</div>', unsafe_allow_html=True)
        
        st.markdown("<h4 style='color: #334155; font-size: 15px; font-weight: 700; margin-bottom: 15px;'>B. Calling Engagement & Recency (LTB/LCB)</h4>", unsafe_allow_html=True)
        st.markdown(f'<div style="display: flex; flex-direction: column; margin-bottom: 25px;">{engagement_html}</div>', unsafe_allow_html=True)
        # ==========================================
        # 🧠 GEMINI AI INJECTION: ACTIVE HEALTH & CALLING (2A & 2B)
        # ==========================================
        if gemini_key:
            health_rubric = """
            Audit active pipeline health focusing on competitor threat, workable aging, and RM calling input across branches.
            - COMPETITOR THREAT & AGING (2A): Flag any branch with a low proportion of Safe Leads or where workable files are stuck aging >7 days. Emphasize that delayed decision-making causes files to slip to competitors.
            - CALLING ENGAGEMENT (2B): Flag branches that have poor Calling Input (high untouched leads or LTB/LCB aging in older buckets). Emphasize the need for disposition discipline.
            - MUST USE LINGO: Exclusive/Safe Leads, Competitor Risk, Stuck Files, Untouched leads, Calling input, Disposition discipline, Recency.
            """
            
            # Dynamically extract 2A & 2B stats for the AI
            branch_health_stats = ""
            for i, b in enumerate(log_y_branches):
                b_act = active_log_df[active_log_df['location'] == b]
                b_work = b_act[b_act['comp_max_stage'] < 4] if not b_act.empty else pd.DataFrame()
                safe_c = b_act[b_act['comp_max_stage'] <= 1].shape[0] if not b_act.empty else 0
                untouched_c = b_work['last_call_date'].isna().sum() if not b_work.empty and 'last_call_date' in b_work.columns else 0
                branch_health_stats += f"- {b}: {b_act.shape[0]} Active | {safe_c} Safe | {log_o7_vals[i]} Stuck (>7d) | {untouched_c} Untouched\n"
            
            health_context = f"""
            Stage: Login Active Pipeline
            Branch-Level Health Metrics:
            {branch_health_stats}
            """
            with st.spinner("Auditing Active Threats and Calling Discipline..."):
                health_insight = generate_executive_insight(health_context, "Active Pipeline Health & Calling Engagement", health_rubric, gemini_key)
                st.markdown(build_ai_insight_card(health_insight), unsafe_allow_html=True)
        
        st.divider()

        # --- ROW 4: QUERY RESOLUTION STATUS (SAAS GRID) ---
        st.markdown('<div class="section-header"><h2>❓ 3. Query Resolution Status (Workable Login Leads)</h2></div>', unsafe_allow_html=True)
        st.markdown("Tracking unresolved bottlenecks vs. resolved queries for **Active Workable** Login leads.")

        res_vals, unres_vals, query_totals = [], [], []

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

        query_cards_html = ""
        for i, b in enumerate(log_y_branches):
            query_cards_html += build_query_saas_card(b, query_totals[i], res_vals[i], unres_vals[i])

        st.markdown(f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 25px;">{query_cards_html}</div>', unsafe_allow_html=True)
        # ==========================================
        # 🧠 GEMINI AI INJECTION: QUERY BOTTLENECKS
        # ==========================================
        if gemini_key:
            query_rubric = """
            Identify operational bottlenecks caused by unresolved queries at the branch level.
            - GOOD PERFORMANCE: All branches have zero unresolved queries.
            - FLAG IMPROVEMENT: Identify any branch carrying unresolved queries. 
            - FORMAT: Keep this insight to a sharp, direct one-liner.
            - MUST USE LINGO: Unresolved queries, Pipeline blockers.
            """
            query_context = f"""
            Branches Tracked: {log_y_branches}
            Total Queries Logged by Branch: {query_totals}
            Resolved Queries: {res_vals}
            Unresolved Queries (Blocking): {unres_vals}
            """
            with st.spinner("Auditing Query Bottlenecks..."):
                query_insight = generate_executive_insight(query_context, "Query Resolution Status", query_rubric, gemini_key)
                st.markdown(build_ai_insight_card(query_insight), unsafe_allow_html=True)
            
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
        # 🧠 GEMINI AI INJECTION: BRANCH LEAKAGE & AUTOPSY
        # ==========================================
        if gemini_key:
            branch_lost_rubric = """
            Analyze branch-level lost potential and the validity of RM loss reasons.
            - STEP 1 (LOST POTENTIAL): Identify which specific branch has the highest "Lost Potential" percentage. Point out that leads distributed to this branch are being abandoned but successfully processed elsewhere.
            - STEP 2 (AUTOPSY/NOT INTERESTED): Cross-reference the loss reasons. If "Not Interested" is a top reason, explicitly flag this as a "Sales Loss". Emphasize that the lead was clearly interested in a loan, as they went and processed it with another bank.
            - MUST USE LINGO: Lost Potential, Sales Loss, Disposition integrity.
            """
            branch_lost_context = f"""
            Branches Tracked: {log_y_branches}
            Total Lost Leads by Branch: {lost_branch_totals}
            Lost Potential Percentages by Branch: {potential_loss_pcts}
            Overall Top Flight Risk Reasons: {top_reasons if 'top_reasons' in locals() else 'None recorded'}
            """
            with st.spinner("Auditing Branch-Level Leakage..."):
                branch_lost_insight = generate_executive_insight(branch_lost_context, "Lost Potential & Flight Risk Autopsy", branch_lost_rubric, gemini_key)
                st.markdown(build_ai_insight_card(branch_lost_insight), unsafe_allow_html=True)
            st.divider()

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
        # ==========================================
        # 🧠 GEMINI AI INJECTION: BRANCH PERFORMANCE
        # ==========================================
        if gemini_key:
            branch_perf_rubric = """
            Audit branch-level performance strictly against the overall Lender Average.
            - GOOD PERFORMANCE: Branch conversion is higher than average and TAT is lower than average.
            - FLAG IMPROVEMENT: Identify any branch with a lower conversion rate than the Lender Average. Also, flag branches with a higher TAT than the Lender Average.
            - MAJOR DOUBLE FLAG: Explicitly call out any branch that is failing on BOTH fronts (lower conversion AND higher TAT).
            - MUST USE LINGO: Lender Average, Double Flag, Processing Speed.
            """
            branch_perf_context = f"""
            Stage: Sanction to PF Paid
            Lender Average Conversion: {lender_avg_conv}% | Lender Average TAT: {lender_avg_tat} days
            Branches Tracked: {san_y_branches}
            Branch Conversion Rates: {conv_rates}
            Branch TAT (Days): {tat_days}
            """
            with st.spinner("Auditing Branch Performance..."):
                branch_insight = generate_executive_insight(branch_perf_context, "Branch Performance Matrix", branch_perf_rubric, gemini_key)
                st.markdown(build_ai_insight_card(branch_insight), unsafe_allow_html=True)

        st.divider()

        # --- ROW 2 & 3: PIPELINE HEALTH & ENGAGEMENT ---
        st.markdown('<div class="section-header"><h2>⏱️ 2. Active Pipeline Health & Competitor Risk</h2></div>', unsafe_allow_html=True)
        
        threat_aging_html = ""
        engagement_html = ""
        
        for b in san_y_branches:
            b_act = active_san_df[active_san_df['location'] == b] if not active_san_df.empty else pd.DataFrame()
            if not b_act.empty:
                b_workable = b_act[b_act['comp_max_stage'] < 4]
                
                threat_card = build_branch_threat_card(b, b_act, 3)
                aging_card = build_branch_aging_card(b, b_workable, 'sanction_date')
                engage_row = build_branch_engagement_row(b, b_workable)
                
                split_row = f"""
                <div style="display: flex; gap: 15px; align-items: stretch; margin-bottom: 15px;">
                    {threat_card}
                    {aging_card}
                </div>
                """
                threat_aging_html += split_row.replace('\n', '').strip()
                
                engage_wrapper = f'<div style="margin-bottom: 10px;">{engage_row}</div>'
                engagement_html += engage_wrapper.replace('\n', '').strip()
                
        st.markdown("<h4 style='color: #334155; font-size: 15px; font-weight: 700; margin-bottom: 15px; margin-top: 10px;'>A. Competitor Threat & Workable Aging</h4>", unsafe_allow_html=True)
        st.markdown(f'<div style="display: flex; flex-direction: column; margin-bottom: 35px;">{threat_aging_html}</div>', unsafe_allow_html=True)
        
        st.markdown("<h4 style='color: #334155; font-size: 15px; font-weight: 700; margin-bottom: 15px;'>B. Calling Engagement & Recency (LTB/LCB)</h4>", unsafe_allow_html=True)
        st.markdown(f'<div style="display: flex; flex-direction: column; margin-bottom: 25px;">{engagement_html}</div>', unsafe_allow_html=True)

        # ==========================================
        # 🧠 GEMINI AI INJECTION: ACTIVE HEALTH & CALLING (2A & 2B)
        # ==========================================
        if gemini_key:
            health_rubric = """
            Audit active pipeline health focusing on competitor threat, workable aging, and RM calling input across branches.
            - COMPETITOR THREAT & AGING (2A): Flag any branch with a low proportion of Safe Leads or where workable files are stuck aging >7 days. Emphasize that delayed decision-making causes files to slip to competitors.
            - CALLING ENGAGEMENT (2B): Flag branches that have poor Calling Input (high untouched leads or LTB/LCB aging in older buckets). Emphasize the need for disposition discipline.
            - MUST USE LINGO: Exclusive/Safe Leads, Competitor Risk, Stuck Files, Untouched leads, Calling input, Disposition discipline, Recency.
            """
            
            # Dynamically extract 2A & 2B stats for the AI
            branch_health_stats = ""
            for i, b in enumerate(san_y_branches):
                b_act = active_san_df[active_san_df['location'] == b]
                b_work = b_act[b_act['comp_max_stage'] < 4] if not b_act.empty else pd.DataFrame()
                # Sanction is deeper in the funnel, so "Safe" is <= 2
                safe_c = b_act[b_act['comp_max_stage'] <= 2].shape[0] if not b_act.empty else 0
                untouched_c = b_work['last_call_date'].isna().sum() if not b_work.empty and 'last_call_date' in b_work.columns else 0
                branch_health_stats += f"- {b}: {b_act.shape[0]} Active | {safe_c} Safe | {san_o7_vals[i]} Stuck (>7d) | {untouched_c} Untouched\n"
            
            health_context = f"""
            Stage: Sanction Active Pipeline
            Branch-Level Health Metrics:
            {branch_health_stats}
            """
            with st.spinner("Auditing Active Threats and Calling Discipline..."):
                health_insight = generate_executive_insight(health_context, "Active Pipeline Health & Calling Engagement", health_rubric, gemini_key)
                st.markdown(build_ai_insight_card(health_insight), unsafe_allow_html=True)
        
        st.divider()

        # --- ROW 3: QUERY RESOLUTION STATUS (SAAS GRID) ---
        st.markdown('<div class="section-header"><h2>❓ 3. Query Resolution Status (Workable Sanction Leads)</h2></div>', unsafe_allow_html=True)
        st.markdown("Tracking unresolved bottlenecks vs. resolved queries for **Active Workable** Sanction leads.")

        res_vals, unres_vals, query_totals = [], [], []

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

        query_cards_html = ""
        for i, b in enumerate(san_y_branches):
            query_cards_html += build_query_saas_card(b, query_totals[i], res_vals[i], unres_vals[i])

        st.markdown(f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 25px;">{query_cards_html}</div>', unsafe_allow_html=True)
        # ==========================================
        # 🧠 GEMINI AI INJECTION: QUERY BOTTLENECKS
        # ==========================================
        if gemini_key:
            query_rubric = """
            Identify operational bottlenecks caused by unresolved queries at the branch level.
            - GOOD PERFORMANCE: All branches have zero unresolved queries.
            - FLAG IMPROVEMENT: Identify any branch carrying unresolved queries. 
            - FORMAT: Keep this insight to a sharp, direct one-liner.
            - MUST USE LINGO: Unresolved queries, Pipeline blockers.
            """
            query_context = f"""
            Branches Tracked: {san_y_branches}
            Total Queries Logged by Branch: {query_totals}
            Resolved Queries: {res_vals}
            Unresolved Queries (Blocking): {unres_vals}
            """
            with st.spinner("Auditing Query Bottlenecks..."):
                query_insight = generate_executive_insight(query_context, "Query Resolution Status", query_rubric, gemini_key)
                st.markdown(build_ai_insight_card(query_insight), unsafe_allow_html=True)
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

            # ==========================================
        # 🧠 GEMINI AI INJECTION: BRANCH LEAKAGE & AUTOPSY
        # ==========================================
        if gemini_key:
            branch_lost_rubric = """
            Analyze branch-level lost potential and the validity of RM loss reasons.
            - STEP 1 (LOST POTENTIAL): Identify which specific branch has the highest "Lost Potential" percentage. Point out that leads distributed to this branch are being abandoned but successfully processed elsewhere.
            - STEP 2 (AUTOPSY/NOT INTERESTED): Cross-reference the loss reasons. If "Not Interested" is a top reason, explicitly flag this as a "Sales Loss". Emphasize that the lead was clearly interested in a loan, as they went and processed it with another bank.
            - MUST USE LINGO: Lost Potential, Sales Loss, Disposition integrity.
            """
            branch_lost_context = f"""
            Branches Tracked: {san_y_branches}
            Total Lost Leads by Branch: {lost_branch_totals}
            Lost Potential Percentages by Branch: {potential_loss_pcts}
            Overall Top Flight Risk Reasons: {top_reasons if 'top_reasons' in locals() else 'None recorded'}
            """
            with st.spinner("Auditing Branch-Level Leakage..."):
                branch_lost_insight = generate_executive_insight(branch_lost_context, "Lost Potential & Flight Risk Autopsy", branch_lost_rubric, gemini_key)
                st.markdown(build_ai_insight_card(branch_lost_insight), unsafe_allow_html=True)

    # ==========================================
    # 🟢 TAB 5: EXECUTIVE BRIEFING
    # ==========================================
    with tab5:
        st.markdown('<div class="section-header"><h2>Executive Synthesis & Action Plan</h2></div>', unsafe_allow_html=True)
        st.markdown("Dynamic AI-generated briefing summarizing pipeline health, branch bottlenecks, and leakage risks across the entire operation.")
        
        # UI: Time Selector
        time_selector = st.radio(
            "Select Briefing Depth:",
            ["☕ 2-Minute Read (Top Priorities)", "📊 5-Minute Read (Operational Review)", "🧠 10-Minute Read (Forensic Audit)"],
            horizontal=True
        )
        
        st.divider()
        
        # Only run the heavy AI generation when the user explicitly asks for it
        if st.button("Generate Briefing", type="primary", use_container_width=True):
            if gemini_key:
                # 1. Bundle all the variables calculated in Tabs 1-4 into one Master String
                master_payload = f"""
                MACRO HEALTH (COHORT):
                - Shared: {tot_shared:,} | Login: {tot_login:,} ({bp_log_pct:.1f}%) | Sanction: {tot_sanc:,} ({log_san_pct:.1f}%) | PF: {tot_pf:,} ({san_pf_pct:.1f}%)
                - Expected Baselines: BP->Log (>70%), Log->San (>50%), San->PF (>50%)
                
                ACTIVE THREATS & AGING:
                - Overall Untouched Leads: (Insert total untouched count here)
                - Stuck Files (>15 Days): BP ({bp_buckets[3]}), Login ({log_buckets[3]}), Sanction ({san_buckets[3]})
                
                BRANCH OUTLIERS (CONVERSION VS TAT):
                - Lender Average BP->Log: {lender_avg_conv}% 
                - Bottom Performing Branches: (Insert lowest converting branches from your lists)
                
                LEAKAGE & AUTOPSY:
                - Top 3 Loss Reasons Given by RMs: {top_reasons[:3] if 'top_reasons' in locals() else 'None'}
                - Branches with Highest Lost Potential: (Insert top branch from potential_loss_pcts)
                """
                
                # 2. Stream the output into a nice container
                with st.container():
                    st.markdown("### 🤖 Live AI Briefing")
                    # st.write_stream gives that smooth typing effect
                    st.write_stream(stream_executive_brief(master_payload, time_selector, gemini_key))
            else:
                st.warning("Please enter your Gemini API Key in the sidebar to generate the briefing.")

    # ==========================================
    # 🟢 TAB 6: CHAT WITH YOUR DATA
    # ==========================================
    with tab6:
        st.markdown('<div class="section-header"><h2>💬 AI Operations Assistant</h2></div>', unsafe_allow_html=True)
        st.markdown("Ask anything about the pipeline, branch performance, or competitor threats.")
        st.divider()

        # Display previous chat messages from memory
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # The Chat Input Box
        if prompt := st.chat_input("E.g., Which branch is bleeding the most leads right now?"):
            
            # 1. Save user message to memory and display it
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # 2. Check for API Key
            if not gemini_key:
                st.error("Please enter your Gemini API Key in the sidebar.")
            else:
                genai.configure(api_key=gemini_key)
                
                # 3. Create the Master Payload (The Bot's Brain)
                # (You can reuse the exact same payload from Tab 5 here)
                bot_brain_payload = f"""
                MACRO HEALTH (COHORT):
                - Shared: {tot_shared:,} | Login: {tot_login:,} ({bp_log_pct:.1f}%) | Sanction: {tot_sanc:,} ({log_san_pct:.1f}%) | PF: {tot_pf:,} ({san_pf_pct:.1f}%)
                - Expected Baselines: BP->Log (>70%), Log->San (>50%), San->PF (>50%)
                
                ACTIVE THREATS & AGING:
                - Stuck Files (>15 Days): BP ({bp_buckets[3]}), Login ({log_buckets[3]}), Sanction ({san_buckets[3]})
                
                BRANCH OUTLIERS (CONVERSION VS TAT):
                - Lender Average BP->Log: {lender_avg_conv}% 
                
                LEAKAGE & AUTOPSY:
                - Top Loss Reasons Given by RMs: {top_reasons if 'top_reasons' in locals() else 'None'}
                """

                # 4. Initialize the AI with System Instructions
                model = genai.GenerativeModel(
                    'gemini-1.5-pro',
                    system_instruction=f"You are an elite Data Operations Manager. You must answer the user's questions based strictly on this live dashboard data: {bot_brain_payload}. Be direct, analytical, and use business ops lingo."
                )

                # 5. Generate and stream the response
                with st.chat_message("assistant"):
                    # We format the memory into a list of dictionaries Gemini understands
                    history = [{"role": m["role"], "parts": [m["content"]]} for m in st.session_state.messages[:-1]]
                    
                    try:
                        chat_session = model.start_chat(history=history)
                        response_stream = chat_session.send_message(prompt, stream=True)
                        
                        # Streamlit's write_stream creates the live typing effect
                        full_response = st.write_stream(chunk.text for chunk in response_stream)
                        
                        # 6. Save the AI's response to memory
                        st.session_state.messages.append({"role": "model", "content": full_response})
                        
                    except Exception as e:
                        st.error(f"Chatbot Offline: {str(e)}")
