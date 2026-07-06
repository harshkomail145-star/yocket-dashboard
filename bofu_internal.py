import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. PAGE SETUP & THEME CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Yocket BOFU Command Center",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- THEME TOGGLE (SIDEBAR) ---
st.sidebar.title("⚙️ Dashboard Controls")
dark_mode = st.sidebar.toggle("🌙 Enable Dark Mode", value=False)

# --- DYNAMIC THEMING VARIABLES ---
if dark_mode:
    plotly_theme = "plotly_dark"
    metric_bg = "#262730"
    metric_text = "#ffffff"
    grid_color = "#444444"
    text_color = "white"
else:
    plotly_theme = "plotly_white"
    metric_bg = "#f8f9fa"
    metric_text = "#31333F"
    grid_color = "#e5e5e5"
    text_color = "black"

st.markdown(f"""
    <style>
    .stMetric {{
        background-color: {metric_bg};
        color: {metric_text};
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #1f77b4;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
    }}
    .macro-metric {{
        border-left: 5px solid #ff9800 !important;
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MASTER FILTER UI
# ==========================================
st.title("🎯 Yocket BOFU Operations Pulse")
st.caption("Executive Dashboard | Live Trajectory, Funnel Tracking & RM Performance")

st.write("---")
st.subheader("🌍 Global Source Filter")
selected_source = st.radio(
    "Filter Entire Dashboard by Lead Source:", 
    ["Overall", "Finco", "Non-Finco", "LS", "GB"], 
    horizontal=True
)
st.divider()

# ==========================================
# 3. DYNAMIC DATA GENERATION ENGINE
# ==========================================
# We use a seed map so the random numbers stay consistent when toggling back and forth
seed_map = {"Overall": 42, "Finco": 101, "Non-Finco": 202, "LS": 303, "GB": 404}

@st.cache_data
def get_lytd_data(source):
    np.random.seed(seed_map[source])
    scale = 1.0 if source == "Overall" else np.random.uniform(0.15, 0.40)
    
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
    
    bp_base = np.array([3000, 3200, 3500, 3100, 4000, 4500, 4800, 3300, 3100, 3800, 3400, 4300, 4800, 5200])
    log_base = np.array([600, 650, 700, 620, 800, 900, 960, 660, 610, 780, 680, 860, 980, 1050])
    sanc_base = np.array([300, 330, 360, 310, 420, 470, 500, 330, 300, 390, 350, 440, 500, 530])
    pf_base = np.array([180, 200, 220, 190, 260, 290, 310, 200, 180, 240, 220, 280, 320, 340])

    df_vol = pd.DataFrame({
        "Month": months * 2,
        "Year": ["LYTD"] * 7 + ["Current"] * 7,
        "BP": (bp_base * scale).astype(int),
        "Logins": (log_base * scale).astype(int),
        "Sanctions": (sanc_base * scale).astype(int),
        "PFs": (pf_base * scale).astype(int)
    })
    
    df_conv = pd.DataFrame({
        "Month": df_vol["Month"], "Year": df_vol["Year"],
        "BP to Login (%)": (df_vol["Logins"] / df_vol["BP"] * 100).round(1),
        "Login to Sanction (%)": (df_vol["Sanctions"] / df_vol["Logins"] * 100).round(1),
        "Sanction to PF (%)": (df_vol["PFs"] / df_vol["Sanctions"] * 100).round(1)
    })
    
    df_multi = pd.DataFrame({
        "Stage": ["BP / Sharing", "Logins", "Sanctions"],
        "LYTD_Ratio": [3.8, 2.0, 1.3], "Current_Ratio": [4.2, 1.9, 1.45], "Target": [4.0, 2.2, 1.7]
    })
    
    df_tat = pd.DataFrame({
        "Conversion Stage": ["BP ➔ Login", "Login ➔ Sanction", "Sanction ➔ PF"],
        "LYTD_Days": [3.5, 5.0, 3.2], "Current_Days": [3.0, 4.2, 2.8]
    })
    return df_vol, df_conv, df_multi, df_tat, scale

@st.cache_data
def get_current_funnel_data(source, scale):
    np.random.seed(seed_map[source])
    
    df_funnel = pd.DataFrame({
        "Stage": ["1. Shared (BP)", "2. Logins", "3. Sanctions", "4. PFs (Won)"],
        "Progressed": (np.array([14200, 7668, 4600, 4600]) * scale).astype(int),
        "Active": (np.array([4200, 2800, 1100, 0]) * scale).astype(int),         
        "Lost": (np.array([3100, 3732, 1968, 0]) * scale).astype(int)            
    })
    
    df_aging = pd.DataFrame({
        "Stage": ["Shared (BP)"]*4 + ["Logins"]*4 + ["Sanctions"]*4,
        "Aging Bucket": ["0-7 Days", "8-14 Days", "15-21 Days", "21+ Days"] * 3,
        "Active Leads": (np.array([2000, 1400, 600, 200, 1200, 1000, 450, 150, 500, 400, 150, 50]) * scale).astype(int)
    })
    
    df_lost_shared = pd.DataFrame({"Reason": ["Unresponsive", "Low Intent", "Already Applied", "Ineligible"], "Count": (np.array([1200, 850, 600, 450]) * scale).astype(int)}).sort_values('Count') 
    df_lost_login = pd.DataFrame({"Reason": ["Low CIBIL", "Low Co-app Income", "Missing Docs", "Property Issue"], "Count": (np.array([1500, 1100, 732, 400]) * scale).astype(int)}).sort_values('Count')
    df_lost_sanction = pd.DataFrame({"Reason": ["Better Rate Elsewhere", "Visa Rejection", "Deferred", "Competitor Matched"], "Count": (np.array([800, 650, 318, 200]) * scale).astype(int)}).sort_values('Count')
    
    df_ltb_lcb = pd.DataFrame({
        "Stage_Metric": ["1. BP - LTB (Touched)", "1. BP - LCB (Connected)", "2. Logins - LTB (Touched)", "2. Logins - LCB (Connected)", "3. Sanctions - LTB (Touched)", "3. Sanctions - LCB (Connected)"],
        "0-3 Days (Good)": (np.array([1800, 900, 1300, 750, 600, 400]) * scale).astype(int),
        "4-7 Days (Warm)": (np.array([1500, 1100, 900, 1000, 300, 450]) * scale).astype(int),
        "8+ Days (Terrible)": (np.array([900, 2200, 600, 1050, 200, 250]) * scale).astype(int)
    })
    return df_funnel, df_aging, df_lost_shared, df_lost_login, df_lost_sanction, df_ltb_lcb

@st.cache_data
def get_rm_data(source):
    np.random.seed(seed_map[source])
    rms = ["Rahul Desai", "Priya Sharma", "Amit Singh", "Sneha Gupta", "Vikram Patel", "Neha Verma", "Rohit Kumar", "Pooja Reddy", "Karan Malhotra", "Anjali Joshi"]
    
    scale_min = 150 if source == "Overall" else 30
    scale_max = 400 if source == "Overall" else 150
    
    shared = np.random.randint(scale_min, scale_max, 10)
    logins = (shared * np.random.uniform(0.15, 0.55, 10)).astype(int)
    sanctions = (logins * np.random.uniform(0.3, 0.75, 10)).astype(int)
    pfs = (sanctions * np.random.uniform(0.4, 0.85, 10)).astype(int)
    
    # NEW: Calculate Lost Leads (Simulating a portion of the leads that didn't move forward being marked as lost)
    lost_bp = ((shared - logins) * np.random.uniform(0.6, 0.9, 10)).astype(int)
    lost_login = ((logins - sanctions) * np.random.uniform(0.5, 0.85, 10)).astype(int)
    lost_sanction = ((sanctions - pfs) * np.random.uniform(0.4, 0.8, 10)).astype(int)
    
    tat_bp_login = np.random.uniform(2.0, 8.5, 10).round(1)
    tat_login_sanc = np.random.uniform(3.0, 11.0, 10).round(1)
    tat_sanc_pf = np.random.uniform(1.5, 7.0, 10).round(1)

    age_bp = np.random.uniform(3.0, 16.0, 10).round(1)
    age_login = np.random.uniform(5.0, 19.0, 10).round(1)
    age_sanc = np.random.uniform(2.0, 14.0, 10).round(1)

    stale_range = 50 if source == "Overall" else 15
    ltb_stale = np.random.randint(2, stale_range, 10)
    lcb_stale = np.random.randint(5, stale_range + 20, 10)
    
    queries_raised = np.random.randint(10, 150, 10)
    queries_resolved = (queries_raised * np.random.uniform(0.3, 0.9, 10)).astype(int)
    unresolved = queries_raised - queries_resolved
    age_unresolved = np.random.uniform(2.0, 14.0, 10).round(1)
    
    df_rm = pd.DataFrame({
        "RM Name": rms,
        "Shared (BP)": shared, "Logins": logins, "Sanctions": sanctions, "PFs (Won)": pfs,
        "BP to Login (%)": (logins / shared * 100).round(1),
        "Login to Sanction (%)": (sanctions / logins * 100).round(1),
        "Sanction to PF (%)": (pfs / sanctions * 100).round(1),
        
        # NEW: Lost Percentages
        "Lost BP (%)": (lost_bp / shared * 100).round(1),
        "Lost Login (%)": (lost_login / logins * 100).round(1),
        "Lost Sanction (%)": (lost_sanction / sanctions * 100).round(1),
        
        "TAT: BP ➔ Login": tat_bp_login,
        "TAT: Login ➔ Sanction": tat_login_sanc,
        "TAT: Sanction ➔ PF": tat_sanc_pf,
        "Avg Age: BP": age_bp,
        "Avg Age: Login": age_login,
        "Avg Age: Sanction": age_sanc,
        "Stale LTB (8+ Days)": ltb_stale,
        "Stale LCB (8+ Days)": lcb_stale,
        "Queries Raised": queries_raised,
        "Queries Resolved": queries_resolved,
        "Unresolved Queries": unresolved,
        "Resolution Rate (%)": (queries_resolved / queries_raised * 100).round(1),
        "Avg Age: Unresolved": age_unresolved
    })
    return df_rm.sort_values(by="PFs (Won)", ascending=False)
@st.cache_data
def get_tofu_data(source, scale):
    np.random.seed(seed_map.get(source, 42))
    
    # 1. TOFU Funnel Volumes (Current)
    vol_capture = int(85000 * scale)
    vol_app_start = int(45000 * scale)
    vol_ready = int(24000 * scale)
    vol_bp = int(21500 * scale) 
    
    lytd_capture = int(vol_capture * np.random.uniform(0.88, 0.95))
    lytd_app_start = int(vol_app_start * np.random.uniform(0.88, 0.95))
    lytd_ready = int(vol_ready * np.random.uniform(0.88, 0.95))
    lytd_bp = int(vol_bp * np.random.uniform(0.88, 0.95))
    
    target_capture = int(100000 * scale)
    target_app_start = int(55000 * scale)
    target_ready = int(30000 * scale)
    target_bp = int(25000 * scale)
    
    tofu_summary = {
        "Capture": {"curr": vol_capture, "lytd": lytd_capture, "target": target_capture},
        "App Start": {"curr": vol_app_start, "lytd": lytd_app_start, "target": target_app_start},
        "Ready": {"curr": vol_ready, "lytd": lytd_ready, "target": target_ready},
        "BP": {"curr": vol_bp, "lytd": lytd_bp, "target": target_bp},
    }
    
    # 2. Month-on-Month Data Generation (FIXED THE MATH HERE!)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
    cap_base = np.array([12000, 11500, 13000, 11000, 14000, 15500, 16000])
    
    # Current Year (Better Conversion Rates)
    curr_cap = (cap_base * scale).astype(int)
    curr_app = (curr_cap * np.random.uniform(0.52, 0.65, 7)).astype(int)
    curr_ready = (curr_app * np.random.uniform(0.52, 0.65, 7)).astype(int)
    curr_bp_arr = (curr_ready * np.random.uniform(0.85, 0.95, 7)).astype(int)
    
    # LYTD (Lower Volume AND Worse Conversion Rates)
    lytd_cap = (curr_cap * np.random.uniform(0.85, 0.92, 7)).astype(int)
    lytd_app = (lytd_cap * np.random.uniform(0.40, 0.50, 7)).astype(int) # Lower conversion!
    lytd_ready = (lytd_app * np.random.uniform(0.40, 0.50, 7)).astype(int) # Lower conversion!
    lytd_bp_arr = (lytd_ready * np.random.uniform(0.75, 0.85, 7)).astype(int) # Lower conversion!
    
    df_tofu_mom = pd.DataFrame({
        "Month": months * 2,
        "Year": ["LYTD"] * 7 + ["Current"] * 7,
        "Capture": np.concatenate([lytd_cap, curr_cap]),
        "App Start": np.concatenate([lytd_app, curr_app]),
        "Ready": np.concatenate([lytd_ready, curr_ready]),
        "BP": np.concatenate([lytd_bp_arr, curr_bp_arr])
    })
    
    # Now when we calculate %, the Current year will be visibly higher than LYTD!
    df_tofu_mom["Cap ➔ App (%)"] = (df_tofu_mom["App Start"] / df_tofu_mom["Capture"] * 100).round(1)
    df_tofu_mom["App ➔ Ready (%)"] = (df_tofu_mom["Ready"] / df_tofu_mom["App Start"] * 100).round(1)
    df_tofu_mom["Ready ➔ BP (%)"] = (df_tofu_mom["BP"] / df_tofu_mom["Ready"] * 100).round(1)
    
    df_tofu_funnel = pd.DataFrame({
        "Stage": ["1. Lead Capture", "2. App Start", "3. Ready to Share", "4. Converted to BP"],
        "Volume": [vol_capture, vol_app_start, vol_ready, vol_bp]
    })
    
    df_tofu_tat = pd.DataFrame({
        "Stage Transition": ["Capture ➔ App Start", "App Start ➔ Ready to Share"],
        "Avg Days": [np.random.uniform(1.5, 4.0), np.random.uniform(2.5, 6.0)]
    }).round(1)
    
    rms = ["Rahul Desai", "Priya Sharma", "Amit Singh", "Sneha Gupta", "Vikram Patel", "Neha Verma", "Rohit Kumar", "Pooja Reddy", "Karan Malhotra", "Anjali Joshi"]
    assigned = np.random.randint(int(5000 * scale), int(12000 * scale), 10)
    ready = (assigned * np.random.uniform(0.2, 0.4, 10)).astype(int)
    
    df_tofu_rm = pd.DataFrame({
        "RM Name": rms,
        "Leads Assigned": assigned,
        "Ready to Share": ready,
        "TOFU Conv (%)": (ready / assigned * 100).round(1)
    }).sort_values(by="Ready to Share", ascending=False)
    
   # ... (Your existing df_tofu_rm code) ...

    # NEW: TOFU Lost Leads Intelligence (Using your EXACT reasons)
    lost_data = []
    
    # 1. Lead Capture (Early Drops)
    lost_data.extend([
        ["1. Lead Capture", "Wrong number", int(12000 * scale), np.random.uniform(0.5, 1.5)],
        ["1. Lead Capture", "Not Responding", int(15000 * scale), np.random.uniform(1.0, 5.0)], # Some are legit, some are fake
        ["1. Lead Capture", "Reason Not Captured", int(5000 * scale), np.random.uniform(0.5, 2.0)], # Lazy RM behavior
        ["1. Lead Capture", "other", int(3000 * scale), np.random.uniform(1.0, 3.0)]
    ])
    
    # 2. App Start (Mid Drops - Intent & Competition)
    lost_data.extend([
        ["2. App Start", "Already in process with other bank", int(8000 * scale), np.random.uniform(3.0, 7.0)],
        ["2. App Start", "Not Interested with Yocket", int(4500 * scale), np.random.uniform(2.0, 5.0)],
        ["2. App Start", "Plan Deferred", int(6000 * scale), np.random.uniform(5.0, 10.0)],
        ["2. App Start", "Already went abroad", int(1500 * scale), np.random.uniform(4.0, 8.0)]
    ])
    
    # 3. Ready to Share (Late Drops - High Bandwidth Waste)
    lost_data.extend([
        ["3. Ready to Share", "Not Doable case", int(4000 * scale), np.random.uniform(8.0, 15.0)], # MASSIVE red flag (Process failure)
        ["3. Ready to Share", "Self-funding", int(2500 * scale), np.random.uniform(7.0, 12.0)],
        ["3. Ready to Share", "Plan Dropped", int(2000 * scale), np.random.uniform(6.0, 14.0)]
    ])
    
    df_tofu_lost = pd.DataFrame(lost_data, columns=["Stage", "Reason", "Count", "Avg Days Wasted"]).round(1)
    
    # ---------------------------------------------------------
    # GENERATING THE "ANOMALY" RED FLAGS DATA FOR THE UI
    # ---------------------------------------------------------
    # Red Flag 1: Fake Hustle (Not responding but dropped in < 3 days)
    total_not_responding = df_tofu_lost[df_tofu_lost["Reason"] == "Not Responding"]["Count"].sum()
    fake_hustle_count = int(total_not_responding * np.random.uniform(0.3, 0.5)) # 30-50% are premature drops
    
    # Red Flag 2: Lazy Logging
    lazy_logging_count = df_tofu_lost[df_tofu_lost["Reason"].isin(["Reason Not Captured", "other"])]["Count"].sum()
    
    # Red Flag 3: Process Failure (Not Doable at the very end of the funnel)
    late_ineligible = df_tofu_lost[(df_tofu_lost["Stage"] == "3. Ready to Share") & (df_tofu_lost["Reason"] == "Not Doable case")]["Count"].sum()
    
    df_anomalies = pd.DataFrame({
        "Flag Type": ["Premature 'Not Responding' (< 3 Days)", "Lazy Logging ('Other' / 'Not Captured')", "Late-Stage 'Not Doable' (Process Failure)"],
        "Count": [fake_hustle_count, lazy_logging_count, late_ineligible],
        "Severity": ["High (SLA Evasion)", "Medium (Data Loss)", "Critical (Bandwidth Waste)"]
    })
    
    # Return both dataframes!
    return tofu_summary, df_tofu_mom, df_tofu_funnel, df_tofu_tat, df_tofu_rm, df_tofu_lost, df_anomalies
@st.cache_data
def get_doable_data(source, scale):
    np.random.seed(seed_map.get(source, 42))
    
    vol_bp = int(21500 * scale)
    
    # 1. System-wide Averages & Waterfall Data
    avg_doable = np.random.uniform(5.8, 6.5)
    avg_shared = np.random.uniform(3.4, 4.2)
    
    total_doable = int(vol_bp * avg_doable)
    total_shared = int(vol_bp * avg_shared)
    missed_opps = total_doable - total_shared
    
    df_waterfall = pd.DataFrame({
        "Metric": ["Max Potential", "Unutilized", "Actually Shared"],
        "Value": [total_doable, -missed_opps, total_shared] 
    })
    
    # 2. Bucket Distribution (System Wide)
    buckets = ["Exactly 3 (Minimum)", "4 to 5 Banks", "6 to 7 Banks", "8+ Banks"]
    base_counts = np.array([4500, 3200, 1500, 800])
    multiplier = vol_bp / base_counts.sum()
    counts = (base_counts * multiplier).astype(int)
    
    df_buckets = pd.DataFrame({
        "Banks Shared Bucket": buckets,
        "Lead Volume": counts
    })
    
    # 3. MoM Trend (Is the operations team closing the gap?)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
    doable_trend = np.random.uniform(5.5, 6.8, 7)
    shared_trend = doable_trend * np.random.uniform(0.55, 0.75, 7) 
    
    df_doable_mom = pd.DataFrame({
        "Month": months,
        "Avg Doable": doable_trend.round(1),
        "Avg Shared": shared_trend.round(1)
    })
    
    return df_waterfall, df_buckets, df_doable_mom

@st.cache_data
def get_intelligent_metrics():
    np.random.seed(42)
    rms = ["Rahul Desai", "Priya Sharma", "Amit Singh", "Sneha Gupta", "Vikram Patel", "Neha Verma", "Rohit Kumar", "Pooja Reddy", "Karan Malhotra", "Anjali Joshi"]
    
    # Generate columns: week0 to week40
    weeks = [f"week{i}" for i in range(41)]
    
    tps_data = []
    ics_data = []
    
    for rm in rms:
        # Generate random weekly scores
        # TPS (Time Per Stage): Let's say range 0.5 to 3.5 (Lower is better)
        tps_weekly = np.random.uniform(0.5, 3.5, 41).round(2)
        # ICS (Inquiry Conversion Score): Range 0.5 to 1.5 (Higher is better)
        ics_weekly = np.random.uniform(0.5, 1.5, 41).round(2)
        
        # Randomly insert some 0.0s to simulate inactivity/taking a week off (15% chance)
        tps_weekly[np.random.rand(41) < 0.15] = 0.0
        ics_weekly[np.random.rand(41) < 0.15] = 0.0
        
        # Calculate overall score ignoring the 0.0 weeks
        overall_tps = np.mean(tps_weekly[tps_weekly > 0]).round(2) if np.any(tps_weekly > 0) else 0.0
        overall_ics = np.mean(ics_weekly[ics_weekly > 0]).round(2) if np.any(ics_weekly > 0) else 0.0
        
        tps_data.append([rm, overall_tps] + tps_weekly.tolist())
        ics_data.append([rm, overall_ics] + ics_weekly.tolist())
        
    df_tps = pd.DataFrame(tps_data, columns=['metric_rm', 'overalltps'] + weeks)
    df_ics = pd.DataFrame(ics_data, columns=['metric_rm', 'overallics'] + weeks)
    
    # Sort by overall scores
    df_tps = df_tps.sort_values('overalltps', ascending=True) # Lowest time is best
    df_ics = df_ics.sort_values('overallics', ascending=False) # Highest conversion is best
    
    # Melt the data for the Heatmaps and Trendlines
    df_tps_melt = df_tps.melt(id_vars=['metric_rm'], value_vars=weeks, var_name='Week', value_name='TPS_Score')
    df_ics_melt = df_ics.melt(id_vars=['metric_rm'], value_vars=weeks, var_name='Week', value_name='ICS_Score')
    
    # Extract week number for chronological X-axis sorting
    df_tps_melt['Week_Num'] = df_tps_melt['Week'].str.replace('week', '').astype(int)
    df_ics_melt['Week_Num'] = df_ics_melt['Week'].str.replace('week', '').astype(int)
    
    df_tps_melt = df_tps_melt.sort_values(['metric_rm', 'Week_Num'])
    df_ics_melt = df_ics_melt.sort_values(['metric_rm', 'Week_Num'])
    
    return df_tps, df_ics, df_tps_melt, df_ics_melt

# ==========================================
# 4. LOAD ALL DATA DYNAMICALLY
# ==========================================
# This ensures all variables, including master_scale, are defined in the main scope before the UI renders.
df_vol, df_conv, df_multi, df_tat, master_scale = get_lytd_data(selected_source)
df_funnel, df_aging, df_lost_shared, df_lost_login, df_lost_sanction, df_ltb_lcb = get_current_funnel_data(selected_source, master_scale)
df_rm = get_rm_data(selected_source)
df_tps, df_ics, df_tps_melt, df_ics_melt = get_intelligent_metrics()
tofu_summary, df_tofu_mom, df_tofu_funnel, df_tofu_tat, df_tofu_rm, df_tofu_lost, df_anomalies = get_tofu_data(selected_source, master_scale)
df_waterfall, df_doable_buckets, df_doable_mom = get_doable_data(selected_source, master_scale)

# ==========================================
# 5. APP TABS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 1. TOFU Lead Journey",
    "📊 2. LYTD & Current BOFU Pipeline", 
    "🧑‍💼 3. RM Performance & SLAs", 
    "🧠 4. Intelligent Metrics (ICS/TPS)"
])
# ==========================================
# 6. TAB 1: TOFU LEAD JOURNEY (PRE-BP)
# ==========================================
with tab1:
    # --- NEW SECTION: TOFU SNAPSHOT CARDS ---
    st.subheader(f"1. Executive TOFU Snapshot ({selected_source})")
    col1, col2, col3, col4 = st.columns(4)
    
    # 1. Lead Capture Card
    curr_cap = tofu_summary["Capture"]["curr"]
    lytd_cap = tofu_summary["Capture"]["lytd"]
    target_cap = tofu_summary["Capture"]["target"]
    delta_cap = ((curr_cap - lytd_cap) / lytd_cap) * 100 if lytd_cap else 0
    
    with col1:
        st.markdown('<div class="macro-metric">', unsafe_allow_html=True)
        st.metric("Lead Capture", f"{curr_cap:,}", f"{delta_cap:+.1f}% vs LYTD")
        st.progress(min(curr_cap / target_cap, 1.0))
        st.caption(f"🎯 **{(curr_cap/target_cap)*100:.1f}%** of Target")

    # 2. App Start Card
    curr_app = tofu_summary["App Start"]["curr"]
    lytd_app = tofu_summary["App Start"]["lytd"]
    target_app = tofu_summary["App Start"]["target"]
    delta_app = ((curr_app - lytd_app) / lytd_app) * 100 if lytd_app else 0
    
    with col2:
        st.metric("App Start", f"{curr_app:,}", f"{delta_app:+.1f}% vs LYTD")
        st.progress(min(curr_app / target_app, 1.0))
        st.caption(f"🎯 **{(curr_app/target_app)*100:.1f}%** of Target")

    # 3. Ready to Share Card
    curr_ready = tofu_summary["Ready"]["curr"]
    lytd_ready = tofu_summary["Ready"]["lytd"]
    target_ready = tofu_summary["Ready"]["target"]
    delta_ready = ((curr_ready - lytd_ready) / lytd_ready) * 100 if lytd_ready else 0
    
    with col3:
        st.metric("Ready to Share", f"{curr_ready:,}", f"{delta_ready:+.1f}% vs LYTD")
        st.progress(min(curr_ready / target_ready, 1.0))
        st.caption(f"🎯 **{(curr_ready/target_ready)*100:.1f}%** of Target")

    # 4. Bank Prospects Card (Transition to BOFU)
    curr_bp = tofu_summary["BP"]["curr"]
    lytd_bp = tofu_summary["BP"]["lytd"]
    target_bp = tofu_summary["BP"]["target"]
    delta_bp = ((curr_bp - lytd_bp) / lytd_bp) * 100 if lytd_bp else 0
    
    with col4:
        st.metric("Bank Prospects", f"{curr_bp:,}", f"{delta_bp:+.1f}% vs LYTD")
        st.progress(min(curr_bp / target_bp, 1.0))
        st.caption(f"🎯 **{(curr_bp/target_bp)*100:.1f}%** of Target")

    st.divider()
    # --- NEW SECTION: MoM TOFU VARIANCE (SIDE-BY-SIDE) ---
    st.subheader("2. Month-on-Month TOFU Variance")
    st.caption("Tracking top-of-funnel volume generation over time (Current vs LYTD).")
    
    col_m1, col_m2, col_m3 = st.columns(3)
    
    def plot_tofu_mom(df, y_col, title, color_lytd, color_curr):
        fig = px.line(
            df, x="Month", y=y_col, color="Year", markers=True,
            color_discrete_sequence=[color_lytd, color_curr], title=title
        )
        fig.update_traces(line=dict(width=3), marker=dict(size=6))
        fig.update_layout(
            template=plotly_theme, margin=dict(t=40, b=0, l=0, r=0), height=280,
            yaxis=dict(title=None, gridcolor=grid_color), xaxis=dict(title=None),
            legend=dict(orientation="h", y=-0.3, title=None)
        )
        return fig
        
    with col_m1:
        # Light blue for LYTD, Dark blue for Current Capture
        st.plotly_chart(plot_tofu_mom(df_tofu_mom, "Capture", "Lead Capture Volume", "#aec7e8", "#2c3e50"), use_container_width=True)
    with col_m2:
        # Light blue for LYTD, Medium blue for App Start
        st.plotly_chart(plot_tofu_mom(df_tofu_mom, "App Start", "App Start Volume", "#aec7e8", "#34495e"), use_container_width=True)
    with col_m3:
        # Light blue for LYTD, Grey/blue for Ready to Share
        st.plotly_chart(plot_tofu_mom(df_tofu_mom, "Ready", "Ready to Share Volume", "#aec7e8", "#7f8c8d"), use_container_width=True)
        
    st.divider()
    # --- NEW SECTION: MoM CONVERSION % (HIGH-TECH UI) ---
    st.subheader("3. MoM Conversion Efficiency (YTD vs LYTD)")
    st.caption("Stage-by-stage conversion health. Are we pushing leads through the top of the funnel more efficiently than last year?")
    
    col_c1, col_c2, col_c3 = st.columns(3)
    
    def plot_tech_conv(df, y_col, title, neon_color):
        fig = px.line(
            df, x="Month", y=y_col, color="Year", 
            # Force the Ghost vs Neon colors
            color_discrete_map={"LYTD": "#7f8c8d", "Current": neon_color}, 
            title=title
        )
        
        # High-tech styling: Thicker lines, 'hexagram' markers for a digital look
        fig.update_traces(
            mode="lines+markers", 
            line=dict(width=3), 
            marker=dict(size=8, symbol="hexagram")
        )
        
        # Unified hover acts like a laser-sight showing both metrics at once
        fig.update_layout(
            template=plotly_theme, margin=dict(t=40, b=0, l=0, r=0), height=300,
            yaxis=dict(title=None, gridcolor=grid_color, ticksuffix="%"), 
            xaxis=dict(title=None, showgrid=False), # Hiding X grid lines for a cleaner UI
            legend=dict(orientation="h", y=-0.3, title=None),
            hovermode="x unified" 
        )
        return fig
        
    with col_c1:
        # Tech Orange
        st.plotly_chart(plot_tech_conv(df_tofu_mom, "Cap ➔ App (%)", "Capture ➔ App Start", "#e67e22"), use_container_width=True)
    with col_c2:
        # Cyber Purple
        st.plotly_chart(plot_tech_conv(df_tofu_mom, "App ➔ Ready (%)", "App Start ➔ Ready", "#9b59b6"), use_container_width=True)
    with col_c3:
        # Neon Green
        st.plotly_chart(plot_tech_conv(df_tofu_mom, "Ready ➔ BP (%)", "Ready ➔ Bank Prospect", "#2ecc71"), use_container_width=True)
        
    st.divider()

    # --- EXISTING FUNNEL UI ---
    st.subheader("2. Top of Funnel (TOFU) Trajectory")
    st.caption("Tracking the 1-to-1 lead journey before they splinter into multiple Bank Prospects (BPs).")
    
    # Extract funnel volumes for custom HTML UI
    vol_cap, vol_app, vol_ready, vol_bp = df_tofu_funnel["Volume"].tolist()
    conv_1 = int((vol_app / vol_cap) * 100) if vol_cap else 0
    conv_2 = int((vol_ready / vol_app) * 100) if vol_app else 0
    conv_3 = int((vol_bp / vol_ready) * 100) if vol_ready else 0
    
    arrow_col = "#aaaaaa" if dark_mode else "#7f8c8d"
    
    # Custom HTML Funnel for TOFU
    tofu_funnel_html = f"""
    <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; padding: 20px 0; font-family: sans-serif;">
        <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
            <div style="background-color: #2c3e50; color: white; height: 120px; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 28px; font-weight: bold; border-radius: 4px;">{vol_cap:,}</div>
            <div style="margin-top: 15px; font-size: 16px; font-weight: bold; color: {text_color};">Lead Capture</div>
        </div>
        <div style="flex: 0.3; text-align: center; font-size: 20px; font-weight: bold; color: {arrow_col}; margin-top: -30px;">{conv_1}% ➔</div>
        
        <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
            <div style="background-color: #34495e; color: white; height: 100px; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 26px; font-weight: bold; border-radius: 4px;">{vol_app:,}</div>
            <div style="margin-top: 15px; font-size: 16px; font-weight: bold; color: {text_color};">App Start</div>
        </div>
        <div style="flex: 0.3; text-align: center; font-size: 20px; font-weight: bold; color: {arrow_col}; margin-top: -30px;">{conv_2}% ➔</div>
        
        <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
            <div style="background-color: #7f8c8d; color: white; height: 80px; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold; border-radius: 4px;">{vol_ready:,}</div>
            <div style="margin-top: 15px; font-size: 16px; font-weight: bold; color: {text_color};">Ready to Share</div>
        </div>
        <div style="flex: 0.3; text-align: center; font-size: 20px; font-weight: bold; color: {arrow_col}; margin-top: -30px;">{conv_3}% ➔</div>
        
        <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
            <div style="background-color: #95a5a6; color: white; height: 60px; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: bold; border-radius: 4px;">{vol_bp:,}</div>
            <div style="margin-top: 15px; font-size: 16px; font-weight: bold; color: {text_color};">Bank Prospects</div>
        </div>
    </div>
    """
    st.markdown(tofu_funnel_html.replace('\n', ''), unsafe_allow_html=True)
    
    st.divider()

    # --- UPGRADED SECTION: TOFU LOST LEADS & ANOMALIES ---
    st.subheader("4. Lost Lead Intelligence & Operational Red Flags")
    st.caption("Analyzing drop reasons and automatically flagging suspicious RM behaviors and process failures.")
    
    col_tree, col_flags = st.columns([1.3, 1])
    
    with col_tree:
        st.write("**Top Drop Reasons by Stage (Treemap)**")
        # Treemap showing exactly where the bleeding is happening
        fig_tree = px.treemap(
            df_tofu_lost, 
            path=["Stage", "Reason"], 
            values="Count",
            color="Count",
            color_continuous_scale="Reds", 
        )
        fig_tree.update_traces(
            textinfo="label+value+percent parent", 
            textfont=dict(size=14, color="white")
        )
        fig_tree.update_layout(
            template=plotly_theme, height=400, margin=dict(t=20, b=0, l=0, r=0),
            coloraxis_showscale=False 
        )
        st.plotly_chart(fig_tree, use_container_width=True)

    with col_flags:
        st.write("**🚨 Automated Anomaly Detection**")
        st.caption("System-identified operational leaks requiring immediate Floor Manager intervention.")
        
        # High-Tech Horizontal Bar Chart for Anomalies
        fig_flags = px.bar(
            df_anomalies.sort_values(by="Count", ascending=True), 
            x="Count", 
            y="Flag Type", 
            color="Severity",
            orientation="h",
            text_auto=".2s",
            color_discrete_map={
                "Critical (Bandwidth Waste)": "#c0392b", # Dark Red
                "High (SLA Evasion)": "#e74c3c",       # Bright Red
                "Medium (Data Loss)": "#f39c12"        # Orange
            }
        )
        fig_flags.update_layout(
            template=plotly_theme, height=220, margin=dict(t=20, b=0, l=0, r=0),
            yaxis_title=None, xaxis_title="Total Leads Flagged",
            legend=dict(orientation="b", y=-0.3, title=None)
        )
        fig_flags.update_traces(textposition="outside", textfont_size=12, cliponaxis=False, textfont=dict(color=text_color))
        st.plotly_chart(fig_flags, use_container_width=True)
        
        # Adding a direct Business Insight text box below the chart
        st.markdown(f"""
        <div style="background-color: {metric_bg}; padding: 15px; border-radius: 8px; border-left: 5px solid #e74c3c; box-shadow: 1px 1px 3px rgba(0,0,0,0.1);">
            <h4 style="margin-top:0px; margin-bottom:5px; color:{text_color}; font-size:16px;">💡 Key Action Items:</h4>
            <ul style="color:{text_color}; font-size: 13px; margin-bottom:0px;">
                <li><b>{df_anomalies.iloc[0]['Count']:,} Leads</b> were marked <i>"Not Responding"</i> but dropped in under 3 days. Audit RM attempt logs.</li>
                <li><b>{df_anomalies.iloc[2]['Count']:,} Leads</b> made it all the way to <i>"Ready to Share"</i> before being marked <i>"Not Doable"</i>, wasting ~10 days of processing bandwidth per lead.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
    # --- NEW SECTION: DOABLE VS SHARED (MACRO BUSINESS METRICS) ---
    st.subheader("5. The 'Left on the Table' Analysis (Doable vs. Shared)")
    st.caption("System-wide analysis of sharing potential. Are we maximizing bank exposure or defaulting to the mandatory minimum?")
    
    col_d1, col_d2, col_d3 = st.columns(3)
    
    with col_d1:
        st.write("**The 'Bare Minimum' Syndrome**")
        
        # Donut chart showing systemic laziness
        fig_donut = px.pie(
            df_doable_buckets, names="Banks Shared Bucket", values="Lead Volume", hole=0.6,
            color="Banks Shared Bucket",
            color_discrete_map={
                "Exactly 3 (Minimum)": "#e74c3c", # Red = Bad behavior
                "4 to 5 Banks": "#f39c12", 
                "6 to 7 Banks": "#3498db", 
                "8+ Banks": "#2ecc71"
            }
        )
        fig_donut.update_traces(textinfo="percent", textfont_size=14, marker=dict(line=dict(color=metric_bg, width=2)))
        fig_donut.update_layout(template=plotly_theme, height=320, margin=dict(t=10, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.2, title=None))
        
        avg_sys_ratio = int((df_doable_mom["Avg Shared"].mean() / df_doable_mom["Avg Doable"].mean()) * 100)
        fig_donut.add_annotation(text=f"{avg_sys_ratio}%<br>D2S", x=0.5, y=0.5, font_size=20, font_weight="bold", showarrow=False, font_color=text_color)
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_d2:
        st.write("**System-Wide Missed Opportunities**")
        
        # Waterfall Chart: Visually quantifies lost pipeline volume
        fig_wf = go.Figure(go.Waterfall(
            name="Shares", orientation="v",
            measure=["absolute", "relative", "total"],
            x=df_waterfall["Metric"],
            textposition="outside",
            text=[f"{v:,}" for v in df_waterfall['Value'].abs()],
            y=df_waterfall["Value"],
            decreasing={"marker": {"color": "#e74c3c"}}, # Red for the drop
            totals={"marker": {"color": "#3498db"}},      # Blue for the final actual
            increasing={"marker": {"color": "#7f8c8d"}}   # Grey for the potential
        ))
        fig_wf.update_layout(
            template=plotly_theme, height=320, margin=dict(t=10, b=0, l=0, r=0),
            yaxis_title=None, xaxis_title=None, showlegend=False
        )
        st.plotly_chart(fig_wf, use_container_width=True)

    with col_d3:
        st.write("**MoM Hustle Gap (Avg per Lead)**")
        
        # Line Chart tracking the trend
        df_mom_melt = df_doable_mom.melt(id_vars="Month", value_vars=["Avg Doable", "Avg Shared"], var_name="Metric", value_name="Avg Banks")
        fig_hustle = px.line(
            df_mom_melt, x="Month", y="Avg Banks", color="Metric", markers=True,
            color_discrete_map={"Avg Doable": "#7f8c8d", "Avg Shared": "#3498db"}
        )
        fig_hustle.update_traces(line=dict(width=3), marker=dict(size=8))
        fig_hustle.update_layout(
            template=plotly_theme, height=320, margin=dict(t=10, b=0, l=0, r=0),
            yaxis=dict(title=None, gridcolor=grid_color), xaxis=dict(title=None),
            legend=dict(orientation="h", y=-0.2, title=None), hovermode="x unified"
        )
        st.plotly_chart(fig_hustle, use_container_width=True)

# ==========================================
# 5. TAB 1: LYTD PERFORMANCE & CURRENT PIPELINE
# ==========================================
with tab2:
    st.subheader(f"1. Executive Snapshot ({selected_source})")
    col1, col2, col3, col4 = st.columns(4)

    # Dynamically scaling the targets so the progress bars make sense for sub-sources
    target_bp = int(30000 * master_scale)
    target_logins = int(16000 * master_scale)
    target_sanctions = int(10000 * master_scale)
    target_pfs = int(6000 * master_scale)

    # Calculating Current vs LYTD to feed the Delta (Green/Red arrows)
    curr_bp = df_vol[df_vol["Year"]=="Current"]["BP"].sum()
    lytd_bp = df_vol[df_vol["Year"]=="LYTD"]["BP"].sum()
    delta_bp = ((curr_bp - lytd_bp) / lytd_bp) * 100 if lytd_bp else 0

    curr_logins = df_vol[df_vol["Year"]=="Current"]["Logins"].sum()
    lytd_logins = df_vol[df_vol["Year"]=="LYTD"]["Logins"].sum()
    delta_logins = ((curr_logins - lytd_logins) / lytd_logins) * 100 if lytd_logins else 0

    curr_sanctions = df_vol[df_vol["Year"]=="Current"]["Sanctions"].sum()
    lytd_sanctions = df_vol[df_vol["Year"]=="LYTD"]["Sanctions"].sum()
    delta_sanctions = ((curr_sanctions - lytd_sanctions) / lytd_sanctions) * 100 if lytd_sanctions else 0

    curr_pfs = df_vol[df_vol["Year"]=="Current"]["PFs"].sum()
    lytd_pfs = df_vol[df_vol["Year"]=="LYTD"]["PFs"].sum()
    delta_pfs = ((curr_pfs - lytd_pfs) / lytd_pfs) * 100 if lytd_pfs else 0

    with col1:
        st.markdown('<div class="macro-metric">', unsafe_allow_html=True)
        # Added the delta parameter back in here
        st.metric("BP / Shared", f"{curr_bp:,}", f"{delta_bp:+.1f}% vs LYTD")
        st.progress(min(curr_bp / target_bp, 1.0))
        st.caption(f"🎯 **{(curr_bp/target_bp)*100:.1f}%** of Target")

    with col2:
        st.metric("Logins", f"{curr_logins:,}", f"{delta_logins:+.1f}% vs LYTD")
        st.progress(min(curr_logins / target_logins, 1.0))
        st.caption(f"🎯 **{(curr_logins/target_logins)*100:.1f}%** of Target")

    with col3:
        st.metric("Sanctions", f"{curr_sanctions:,}", f"{delta_sanctions:+.1f}% vs LYTD")
        st.progress(min(curr_sanctions / target_sanctions, 1.0))
        st.caption(f"🎯 **{(curr_sanctions/target_sanctions)*100:.1f}%** of Target")

    with col4:
        st.metric("PFs", f"{curr_pfs:,}", f"{delta_pfs:+.1f}% vs LYTD")
        st.progress(min(curr_pfs / target_pfs, 1.0))
        st.caption(f"🎯 **{(curr_pfs/target_pfs)*100:.1f}%** of Target")

    st.divider()
    
    st.subheader("2. Month-on-Month Volume Variance")
    vol_metric = st.selectbox("Select Metric to View Variance:", ["BP", "Logins", "Sanctions", "PFs"], index=1)
    fig_vol = px.bar(df_vol, x="Month", y=vol_metric, color="Year", barmode="group", color_discrete_sequence=["#aec7e8", "#1f77b4"])
    fig_vol.update_layout(template=plotly_theme, margin=dict(t=20, b=0, l=0, r=0), height=300, legend=dict(orientation="h", y=-0.2, title=None))
    st.plotly_chart(fig_vol, use_container_width=True)

    st.divider()

    st.subheader("3. Month-on-Month Conversion Variance")
    st.caption("Tracking stage-to-stage conversion efficiency over time (Current vs LYTD).")
    conv_metric = st.selectbox("Select Conversion Stage to View Variance:", ["BP to Login (%)", "Login to Sanction (%)", "Sanction to PF (%)"], index=0)
    fig_conv = px.line(df_conv, x="Month", y=conv_metric, color="Year", markers=True, color_discrete_sequence=["#aec7e8", "#ff9800"])
    fig_conv.update_traces(line=dict(width=3), marker=dict(size=8))
    fig_conv.update_layout(template=plotly_theme, margin=dict(t=20, b=0, l=0, r=0), height=300, yaxis=dict(title=None, gridcolor=grid_color), xaxis=dict(title=None), legend=dict(orientation="h", y=-0.2, title=None))
    st.plotly_chart(fig_conv, use_container_width=True)

    st.divider()

    col_multi, col_tat = st.columns([1.2, 1])
    with col_multi:
        st.subheader("4. Multi-Rate Comparison")
        df_multi_melted = df_multi.melt(id_vars=["Stage", "Target"], value_vars=["LYTD_Ratio", "Current_Ratio"], var_name="Year", value_name="Ratio").replace({"LYTD_Ratio": "LYTD", "Current_Ratio": "Current"})
        fig_multi = px.bar(df_multi_melted, x="Stage", y="Ratio", color="Year", barmode="group", color_discrete_sequence=["#aec7e8", "#2ca02c"], text_auto='.2f')
        for i, row in df_multi.iterrows():
            fig_multi.add_shape(type="line", x0=i-0.4, x1=i+0.4, y0=row["Target"], y1=row["Target"], line=dict(color="red", width=2, dash="dash"))
        fig_multi.update_layout(template=plotly_theme, height=300, margin=dict(t=20, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.2, title=None))
        st.plotly_chart(fig_multi, use_container_width=True)

    with col_tat:
        st.subheader("5. TAT Variance (Days)")
        st.write("##")
        for _, row in df_tat.iterrows():
            st.metric(f"⏳ {row['Conversion Stage']}", f"{row['Current_Days']} Days", f"{row['Current_Days'] - row['LYTD_Days']:+.1f} Days vs LYTD", delta_color="inverse")

    st.divider()
    
    st.write(f"## Current Year Funnel Intelligence ({selected_source})")
    col_funnel, col_aging = st.columns([1.5, 1])
    
    with col_funnel:
        st.subheader("6. Conversion Cohort Status")
        val_shared, val_login, val_sanction, val_pf = df_funnel["Progressed"].tolist()
        act_shared, act_login, act_sanction, act_pf = df_funnel["Active"].tolist()
        lost_shared, lost_login, lost_sanction, lost_pf = df_funnel["Lost"].tolist()
        conv_1 = int((val_login / val_shared) * 100) if val_shared else 0
        conv_2 = int((val_sanction / val_login) * 100) if val_login else 0
        conv_3 = int((val_pf / val_sanction) * 100) if val_sanction else 0
        
        arrow_col = "#aaaaaa" if dark_mode else "#7f8c8d"
        
        custom_funnel_html = f"""
        <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; padding: 20px 0; font-family: sans-serif;">
            <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
                <div style="background-color: #4a47d3; color: white; height: 120px; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 28px; font-weight: bold; border-radius: 2px;">{val_shared:,}</div>
                <div style="margin-top: 15px; font-size: 16px; font-weight: bold; color: {text_color};">Shared</div>
                <div style="font-size: 12px; margin-top: 5px;"><span style="color: #e74c3c; font-weight: bold;">{lost_shared:,} Lost</span> <span style="color: {text_color};">|</span> <span style="color: #2ecc71; font-weight: bold;">{act_shared:,} Active</span></div>
            </div>
            <div style="flex: 0.3; text-align: center; font-size: 20px; font-weight: bold; color: {arrow_col}; margin-top: -50px;">{conv_1}% ➔</div>
            <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
                <div style="background-color: #605ee0; color: white; height: 100px; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 26px; font-weight: bold; border-radius: 2px;">{val_login:,}</div>
                <div style="margin-top: 15px; font-size: 16px; font-weight: bold; color: {text_color};">Login</div>
                <div style="font-size: 12px; margin-top: 5px;"><span style="color: #e74c3c; font-weight: bold;">{lost_login:,} Lost</span> <span style="color: {text_color};">|</span> <span style="color: #2ecc71; font-weight: bold;">{act_login:,} Active</span></div>
            </div>
            <div style="flex: 0.3; text-align: center; font-size: 20px; font-weight: bold; color: {arrow_col}; margin-top: -50px;">{conv_2}% ➔</div>
            <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
                <div style="background-color: #7c7bee; color: white; height: 80px; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold; border-radius: 2px;">{val_sanction:,}</div>
                <div style="margin-top: 15px; font-size: 16px; font-weight: bold; color: {text_color};">Sanction</div>
                <div style="font-size: 12px; margin-top: 5px;"><span style="color: #e74c3c; font-weight: bold;">{lost_sanction:,} Lost</span> <span style="color: {text_color};">|</span> <span style="color: #2ecc71; font-weight: bold;">{act_sanction:,} Active</span></div>
            </div>
            <div style="flex: 0.3; text-align: center; font-size: 20px; font-weight: bold; color: {arrow_col}; margin-top: -50px;">{conv_3}% ➔</div>
            <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
                <div style="background-color: #9c9cf5; color: white; height: 60px; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: bold; border-radius: 2px;">{val_pf:,}</div>
                <div style="margin-top: 15px; font-size: 16px; font-weight: bold; color: {text_color};">PF</div>
                <div style="font-size: 12px; margin-top: 5px;"><span style="color: #e74c3c; font-weight: bold;">{lost_pf:,} Lost</span> <span style="color: {text_color};">|</span> <span style="color: #2ecc71; font-weight: bold;">{act_pf:,} Active</span></div>
            </div>
        </div>
        """
        st.markdown(custom_funnel_html.replace('\n', ''), unsafe_allow_html=True)
        
    with col_aging:
        st.subheader("7. Active Pipeline Aging")
        fig_aging = px.bar(df_aging, y="Stage", x="Active Leads", color="Aging Bucket", orientation='h', 
                           color_discrete_map={"0-7 Days": "#2ca02c", "8-14 Days": "#ffc107", "15-21 Days": "#ff7f0e", "21+ Days": "#d62728"},
                           category_orders={"Aging Bucket": ["0-7 Days", "8-14 Days", "15-21 Days", "21+ Days"]})
        fig_aging.update_layout(template=plotly_theme, height=300, barmode="stack", margin=dict(t=20, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.3, title=None))
        st.plotly_chart(fig_aging, use_container_width=True)

    st.write("##")
    st.subheader("8. Lead Engagement: LTB & LCB Health")
    df_ltb_melted = df_ltb_lcb.melt(id_vars="Stage_Metric", var_name="Health Status", value_name="Leads")
    fig_ltb = px.bar(df_ltb_melted, y="Stage_Metric", x="Leads", color="Health Status", orientation='h', 
                     color_discrete_map={"0-3 Days (Good)": "#2ecc71", "4-7 Days (Warm)": "#f39c12", "8+ Days (Terrible)": "#e74c3c"}, text_auto='.2s')
    fig_ltb.update_layout(template=plotly_theme, height=300, barmode="stack", margin=dict(t=20, b=0, l=0, r=0), yaxis={'categoryorder': 'category descending', 'title': None}, xaxis={'title': None, 'showgrid': False, 'showticklabels': False}, legend=dict(orientation="h", y=-0.15, title=None))
    fig_ltb.update_traces(textposition="inside", textfont_size=13, textangle=0)
    st.plotly_chart(fig_ltb, use_container_width=True)
    
    st.divider()
    
    st.subheader("9. Lost Pipeline Diagnostics")
    st.caption("Top reasons for dropped leads at each major conversion stage, ranked highest to lowest.")
    col_lost1, col_lost2, col_lost3 = st.columns(3)
    
    def plot_lost_reasons(df, title, color):
        fig = px.bar(df, y="Reason", x="Count", orientation='h', title=title, color_discrete_sequence=[color], text_auto='.2s')
        fig.update_layout(template=plotly_theme, height=280, margin=dict(t=40, b=0, l=0, r=20), yaxis_title=None, xaxis_title=None, xaxis=dict(showgrid=False, showticklabels=False))
        fig.update_traces(textposition="outside", textfont_size=12, cliponaxis=False, textfont=dict(color=text_color))
        return fig
    
    with col_lost1:
        st.plotly_chart(plot_lost_reasons(df_lost_shared, "Shared ➔ Lost", "#e74c3c"), use_container_width=True)
    with col_lost2:
        st.plotly_chart(plot_lost_reasons(df_lost_login, "Login ➔ Lost", "#e67e22"), use_container_width=True)
    with col_lost3:
        st.plotly_chart(plot_lost_reasons(df_lost_sanction, "Sanction ➔ Lost", "#c0392b"), use_container_width=True)

# ==========================================
# 6. TAB 2: RM PERFORMANCE & BOTTLENECKS
# ==========================================
with tab3:
    st.write(f"## 🧑‍💼 Relationship Manager Command Center ({selected_source})")
    st.caption("Tracking individual operational volume, conversion bottlenecks, TAT delays, and SLA discipline.")
    
    st.subheader("1. The Apex Performers (Volume Leaderboard)")
    df_rm_melted = df_rm.melt(id_vars="RM Name", value_vars=["Shared (BP)", "Logins", "Sanctions", "PFs (Won)"], var_name="Stage", value_name="Volume")
    fig_rm_vol = px.bar(df_rm_melted, x="RM Name", y="Volume", color="Stage", barmode="group",
                        color_discrete_map={"Shared (BP)": "#8e44ad", "Logins": "#1f77b4", "Sanctions": "#2ca02c", "PFs (Won)": "#ff9800"}, text_auto='.2s')
    fig_rm_vol.update_layout(template=plotly_theme, height=350, margin=dict(t=20, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.2, title=None), xaxis_title=None, yaxis_title=None)
    fig_rm_vol.update_traces(textposition="outside", textfont_size=12, cliponaxis=False, textfont=dict(color=text_color))
    st.plotly_chart(fig_rm_vol, use_container_width=True)

    st.divider()

    st.subheader("2. Conversion Leaks (The Bottom 5 RMs)")
    st.caption("Isolating the 5 RMs dragging down our conversion rates at each critical stage.")
    col_bot1, col_bot2, col_bot3 = st.columns(3)
    
    def plot_bottom_5(df, col_name, title, color):
        df_bot = df.nsmallest(5, col_name).sort_values(col_name, ascending=False)
        fig = px.bar(df_bot, y="RM Name", x=col_name, orientation='h', title=title, text_auto='.1f', color_discrete_sequence=[color])
        fig.update_layout(template=plotly_theme, height=250, margin=dict(t=40, b=0, l=0, r=20), yaxis_title=None, xaxis_title=None, xaxis=dict(showticklabels=False, showgrid=False))
        fig.update_traces(textposition="outside", textfont_size=12, cliponaxis=False, textfont=dict(color=text_color))
        return fig
        
    with col_bot1:
        st.plotly_chart(plot_bottom_5(df_rm, "BP to Login (%)", "BP ➔ Login (%)", "#e74c3c"), use_container_width=True)
    with col_bot2:
        st.plotly_chart(plot_bottom_5(df_rm, "Login to Sanction (%)", "Login ➔ Sanction (%)", "#e67e22"), use_container_width=True)
    with col_bot3:
        st.plotly_chart(plot_bottom_5(df_rm, "Sanction to PF (%)", "Sanction ➔ PF (%)", "#c0392b"), use_container_width=True)

    st.divider()

    st.subheader("3. Turnaround Time (TAT) Heatmap")
    st.caption("Visually identifying which RMs process leads the slowest (Red = Slower/Terrible, Blue = Faster/Good).")
    df_tat_heat = df_rm[["RM Name", "TAT: BP ➔ Login", "TAT: Login ➔ Sanction", "TAT: Sanction ➔ PF"]].set_index("RM Name")
    fig_heat = px.imshow(df_tat_heat, text_auto=".1f", aspect="auto", color_continuous_scale="RdBu_r")
    fig_heat.update_layout(template=plotly_theme, height=350, margin=dict(t=20, b=0, l=0, r=0), xaxis_title=None)
    st.plotly_chart(fig_heat, use_container_width=True)

    st.divider()

    col_aging, col_engage = st.columns(2)
    with col_aging:
        st.subheader("4. Active Aging: Who holds stale leads?")
        st.caption("Average number of days an RM's active leads have been sitting in stage.")
        df_age_melt = df_rm.melt(id_vars="RM Name", value_vars=["Avg Age: BP", "Avg Age: Login", "Avg Age: Sanction"], var_name="Stage", value_name="Avg Days")
        fig_aging_rm = px.bar(df_age_melt, x="RM Name", y="Avg Days", color="Stage", barmode="group",
                              color_discrete_map={"Avg Age: BP": "#ffc107", "Avg Age: Login": "#ff9800", "Avg Age: Sanction": "#f44336"})
        fig_aging_rm.update_layout(template=plotly_theme, height=350, margin=dict(t=20, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.2, title=None), xaxis_title=None)
        st.plotly_chart(fig_aging_rm, use_container_width=True)

    with col_engage:
        st.subheader("5. Engagement Blackholes")
        st.caption("Total count of leads sitting in LTB/LCB 'Terrible' (8+ Days) bucket per RM.")
        df_stale = df_rm.sort_values(by="Stale LCB (8+ Days)", ascending=False)
        df_stale_melt = df_stale.melt(id_vars="RM Name", value_vars=["Stale LTB (8+ Days)", "Stale LCB (8+ Days)"], var_name="Metric", value_name="Stale Leads")
        fig_stale = px.bar(df_stale_melt, x="RM Name", y="Stale Leads", color="Metric", barmode="group",
                           color_discrete_map={"Stale LTB (8+ Days)": "#8e44ad", "Stale LCB (8+ Days)": "#c0392b"})
        fig_stale.update_layout(template=plotly_theme, height=350, margin=dict(t=20, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.2, title=None), xaxis_title=None)
        st.plotly_chart(fig_stale, use_container_width=True)
        
    st.divider()

    st.subheader("6. Query Resolution & Operational Blockers")
    st.caption("Tracking bank/counselor queries raised on RM files, resolution speed, and aging of unresolved blockers.")
    col_q1, col_q2 = st.columns(2)
    
    with col_q1:
        st.write("**Query Resolution Efficiency (%)**")
        df_q_rate = df_rm.sort_values(by="Resolution Rate (%)", ascending=True)
        fig_q_rate = px.bar(df_q_rate, y="RM Name", x="Resolution Rate (%)", orientation="h", color="Resolution Rate (%)", color_continuous_scale="RdYlGn", text_auto=".1f")
        fig_q_rate.update_layout(template=plotly_theme, height=350, margin=dict(t=20, b=0, l=0, r=0), yaxis_title=None, xaxis_title="Resolution %", coloraxis_showscale=False)
        fig_q_rate.update_traces(textposition="outside", textfont_size=12, cliponaxis=False, textfont=dict(color=text_color))
        st.plotly_chart(fig_q_rate, use_container_width=True)

    with col_q2:
        st.write("**Unresolved Queries & Aging Heat**")
        df_unresolved = df_rm.sort_values(by="Unresolved Queries", ascending=True)
        fig_q_age = px.bar(df_unresolved, y="RM Name", x="Unresolved Queries", orientation="h", color="Avg Age: Unresolved", text="Unresolved Queries",
                           color_continuous_scale="Reds", labels={"Avg Age: Unresolved": "Avg Days Old"})
        fig_q_age.update_layout(template=plotly_theme, height=350, margin=dict(t=20, b=0, l=0, r=0), yaxis_title=None, xaxis_title="Total Pending Queries", coloraxis_colorbar=dict(title="Days Old", orientation="h", y=-0.3, thickness=15))
        fig_q_age.update_traces(textposition="outside", textfont_size=12, cliponaxis=False, textfont=dict(color=text_color))
        st.plotly_chart(fig_q_age, use_container_width=True)
        st.divider()

    # --- NEW SECTION: PIPELINE DROPS (HIGHEST LOST %) ---
    st.subheader("3. Pipeline Drops (Highest Lost %)")
    st.caption("Top 5 RMs with the highest percentage of marked 'Lost' leads at each stage.")
    col_drop1, col_drop2, col_drop3 = st.columns(3)
    
    def plot_top_5_lost(df, col_name, title, color):
        # nlargest(5) grabs the highest lost %, sorted ascending so the worst offender is at the top of the chart
        df_drop = df.nlargest(5, col_name).sort_values(col_name, ascending=True)
        fig = px.bar(df_drop, y="RM Name", x=col_name, orientation='h', title=title, text_auto='.1f', color_discrete_sequence=[color])
        fig.update_layout(template=plotly_theme, height=250, margin=dict(t=40, b=0, l=0, r=20), yaxis_title=None, xaxis_title=None, xaxis=dict(showticklabels=False, showgrid=False))
        fig.update_traces(textposition="outside", textfont_size=12, cliponaxis=False, textfont=dict(color=text_color))
        return fig
        
    with col_drop1:
        st.plotly_chart(plot_top_5_lost(df_rm, "Lost BP (%)", "Lost from BP (%)", "#9b59b6"), use_container_width=True)
    with col_drop2:
        st.plotly_chart(plot_top_5_lost(df_rm, "Lost Login (%)", "Lost from Login (%)", "#e67e22"), use_container_width=True)
    with col_drop3:
        st.plotly_chart(plot_top_5_lost(df_rm, "Lost Sanction (%)", "Lost from Sanction (%)", "#c0392b"), use_container_width=True)
# ==========================================
# 7. TAB 3: INTELLIGENT METRICS (ICS & TPS)
# ==========================================
with tab4:
    st.write(f"## 🧠 Intelligent Metrics Command Center")
    st.caption("Deep dive into Time Per Stage (TPS) and Inquiry Conversion Score (ICS) trends across 40 weeks.")
    
    # --- SECTION 1: METRIC TOGGLE ---
    metric_focus = st.radio("Select Metric to Analyze:", ["📈 ICS (Inquiry Conversion Score)", "⏱️ TPS (Time Per Stage)"], horizontal=True)
    
    st.divider()

    # Dynamic variables based on toggle
    if "ICS" in metric_focus:
        df_base = df_ics
        df_melt = df_ics_melt
        overall_col = 'overallics'
        val_col = 'ICS_Score'
        color_scale = "Tealgrn" 
        chart_title = "ICS"
        asc_sort = False # Higher is better
    else:
        df_base = df_tps
        df_melt = df_tps_melt
        overall_col = 'overalltps'
        val_col = 'TPS_Score'
        color_scale = "OrRd" 
        chart_title = "TPS"
        asc_sort = True # Lower is better

    df_leaderboard = df_base.dropna(subset=[overall_col])

    # --- SECTION 2: LEADERBOARDS ---
    st.subheader(f"1. {chart_title} Overall Standings (Top vs Bottom Performers)")
    col_top, col_bot = st.columns(2)
    
    with col_top:
        st.write(f"**Top 5 RMs by Overall {chart_title}**")
        df_top = df_leaderboard.sort_values(overall_col, ascending=asc_sort).head(5)
        # Flip the bar direction for a visual hierarchy
        fig_top = px.bar(df_top.sort_values(overall_col, ascending=not asc_sort), y="metric_rm", x=overall_col, orientation='h', text_auto='.2f', color_discrete_sequence=["#2ecc71"])
        fig_top.update_layout(template=plotly_theme, height=250, margin=dict(t=10, b=0, l=0, r=20), yaxis_title=None, xaxis_title=None, xaxis=dict(showgrid=False, showticklabels=False))
        fig_top.update_traces(textposition="outside", textfont_size=12, cliponaxis=False, textfont=dict(color=text_color))
        st.plotly_chart(fig_top, use_container_width=True)

    with col_bot:
        st.write(f"**Bottom 5 RMs by Overall {chart_title}**")
        df_bot = df_leaderboard.sort_values(overall_col, ascending=not asc_sort).head(5)
        fig_bot = px.bar(df_bot.sort_values(overall_col, ascending=asc_sort), y="metric_rm", x=overall_col, orientation='h', text_auto='.2f', color_discrete_sequence=["#e74c3c"])
        fig_bot.update_layout(template=plotly_theme, height=250, margin=dict(t=10, b=0, l=0, r=20), yaxis_title=None, xaxis_title=None, xaxis=dict(showgrid=False, showticklabels=False))
        fig_bot.update_traces(textposition="outside", textfont_size=12, cliponaxis=False, textfont=dict(color=text_color))
        st.plotly_chart(fig_bot, use_container_width=True)

    st.divider()

    # --- SECTION 3: THE HEATMAP MATRIX ---
    st.subheader(f"2. {chart_title} 40-Week Heatmap Matrix")
    st.caption(f"Blank/dark areas represent 0.0 scores (inactivity).")
    
    heatmap_pivot = df_melt.pivot(index="metric_rm", columns="Week_Num", values=val_col)
    
    fig_matrix = px.imshow(
        heatmap_pivot, 
        aspect="auto",
        color_continuous_scale=color_scale,
        labels=dict(x="Week Number", y="RM Name", color=f"{chart_title} Score")
    )
    fig_matrix.update_xaxes(dtick=2) 
    fig_matrix.update_layout(template=plotly_theme, height=400, margin=dict(t=20, b=20, l=0, r=0))
    st.plotly_chart(fig_matrix, use_container_width=True)

    st.divider()

    # --- SECTION 4: TRAJECTORY TRACKER ---
    st.subheader(f"3. {chart_title} Trajectory Tracker")
    st.caption("Compare the weekly trajectory of specific Relationship Managers.")
    
    default_rms = df_leaderboard.sort_values(overall_col, ascending=asc_sort).head(3)['metric_rm'].tolist()
    selected_rms = st.multiselect(f"Select RMs to Compare {chart_title}:", df_leaderboard['metric_rm'].unique(), default=default_rms)
    
    if selected_rms:
        df_trend = df_melt[df_melt['metric_rm'].isin(selected_rms)]
        df_trend_clean = df_trend.copy()
        df_trend_clean[val_col] = df_trend_clean[val_col].replace(0.0, np.nan)
        
        fig_trend = px.line(
            df_trend_clean, x="Week_Num", y=val_col, color="metric_rm", markers=True,
            labels={"Week_Num": "Week", val_col: f"{chart_title} Score", "metric_rm": "RM Name"}
        )
        fig_trend.update_traces(line=dict(width=3), marker=dict(size=6), connectgaps=True)
        fig_trend.update_layout(
            template=plotly_theme, height=400, margin=dict(t=20, b=0, l=0, r=0),
            legend=dict(orientation="h", y=-0.2, title=None),
            xaxis=dict(dtick=2)
        )
        st.plotly_chart(fig_trend, use_container_width=True)
