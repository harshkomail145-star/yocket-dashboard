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
    .macro-metric {{ border-left: 5px solid #ff9800 !important; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MASTER FILTER UI
# ==========================================
st.title("🎯 Yocket BOFU Operations Pulse")
st.caption("Executive Dashboard | Segmented Trajectory, Pipeline Health & RM Performance")
st.write("---")
st.subheader("🌍 Global Source Filter")
selected_source = st.radio("Filter Entire Dashboard by Lead Source:", ["Overall", "Finco", "Non-Finco", "LS", "GB"], horizontal=True)
st.divider()

seed_map = {"Overall": 42, "Finco": 101, "Non-Finco": 202, "LS": 303, "GB": 404}
master_scale = 1.0 if selected_source == "Overall" else np.random.uniform(0.15, 0.40)

# ==========================================
# 3. UNIFIED DATA ENGINE
# ==========================================
@st.cache_data
def get_master_pipeline(source, scale):
    np.random.seed(seed_map.get(source, 42))
    
    stages = ["Capture", "App Start", "R2S", "Shared", "Login", "Sanction", "PF"]
    vols = [int(v * scale) for v in [85000, 45000, 24000, 21500, 14200, 7668, 4600]]
    
    # 1. Summary Dictionary (Exec Snapshots)
    summary = {}
    for i, stg in enumerate(stages):
        summary[stg] = {
            "curr": vols[i],
            "lytd": int(vols[i] * np.random.uniform(0.85, 0.95)),
            "target": int(vols[i] * 1.15)
        }

    # 2. MoM Variance & Conversion
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
    df_mom = pd.DataFrame({"Month": months * 2, "Year": ["LYTD"] * 7 + ["Current"] * 7})
    base_pattern = np.array([0.8, 0.75, 0.85, 0.7, 0.9, 1.0, 1.05])
    
    for i, stg in enumerate(stages):
        curr_arr = (base_pattern * vols[i] / 6).astype(int)
        lytd_arr = (curr_arr * np.random.uniform(0.80, 0.90, 7)).astype(int)
        df_mom[stg] = np.concatenate([lytd_arr, curr_arr])

    df_mom["Cap ➔ App (%)"] = (df_mom["App Start"] / df_mom["Capture"] * 100).round(1)
    df_mom["App ➔ R2S (%)"] = (df_mom["R2S"] / df_mom["App Start"] * 100).round(1)
    df_mom["R2S ➔ Shr (%)"] = (df_mom["Shared"] / df_mom["R2S"] * 100).round(1)
    df_mom["Shr ➔ Log (%)"] = (df_mom["Login"] / df_mom["Shared"] * 100).round(1)
    df_mom["Log ➔ San (%)"] = (df_mom["Sanction"] / df_mom["Login"] * 100).round(1)
    df_mom["San ➔ PF (%)"]  = (df_mom["PF"] / df_mom["Sanction"] * 100).round(1)

    # 3. Active Pipeline & Aging
    aging_data = []
    for stg in stages:
        tot_act = int(summary[stg]["curr"] * np.random.uniform(0.1, 0.25))
        dist = np.random.dirichlet(np.ones(4)) * tot_act
        for b_idx, b in enumerate(["0-7 Days", "8-14 Days", "15-21 Days", "21+ Days"]):
            aging_data.append([stg, b, int(dist[b_idx])])
    df_aging = pd.DataFrame(aging_data, columns=["Stage", "Aging Bucket", "Active Leads"])

    # 4. LTB / LCB Engagement Health
    health_data = []
    for stg in stages:
        tot_act = df_aging[df_aging["Stage"]==stg]["Active Leads"].sum()
        health_data.append([stg, 
            int(tot_act * 0.6), int(tot_act * 0.3), int(tot_act * 0.1),
            int(tot_act * 0.3), int(tot_act * 0.4), int(tot_act * 0.3)
        ])
    df_health = pd.DataFrame(health_data, columns=["Stage", "LTB: 0-3 Days (Hot)", "LTB: 4-7 Days (Warm)", "LTB: 8+ Days (Zombie)", "LCB: 0-3 Days (Hot)", "LCB: 4-7 Days (Warm)", "LCB: 8+ Days (Zombie)"])

    # 5. Lost Analysis
    df_lost = pd.DataFrame([
        ["Capture", "Wrong number", int(12000*scale)], ["Capture", "Not Responding", int(15000*scale)], ["Capture", "Reason Not Captured", int(5000*scale)],
        ["App Start", "Already in process", int(8000*scale)], ["App Start", "Not Interested", int(4500*scale)],
        ["R2S", "Not Doable case", int(4000*scale)], ["R2S", "Missing Docs", int(2500*scale)],
        ["Shared", "Unresponsive", int(1200*scale)], ["Shared", "Low Intent", int(850*scale)],
        ["Login", "Low CIBIL", int(1500*scale)], ["Login", "Property Issue", int(1100*scale)],
        ["Sanction", "Better Rate Elsewhere", int(800*scale)], ["Sanction", "Visa Rejection", int(650*scale)]
    ], columns=["Stage", "Reason", "Count"])

    # 6. Tab Specific Anomalies
    ano_t1 = pd.DataFrame({"Flag Type": ["Premature 'Not Responding'", "Lazy Logging ('Not Captured')"], "Count": [int(15000*scale*0.4), int(5000*scale)], "Severity": ["High (SLA Evasion)", "Medium (Data Loss)"]})
    ano_t2 = pd.DataFrame({"Flag Type": ["Late 'Not Doable'", "Shared but Unresponsive"], "Count": [int(4000*scale), int(1200*scale)], "Severity": ["Critical (Bandwidth Waste)", "High (Ghosting)"]})
    ano_t3 = pd.DataFrame({"Flag Type": ["Low CIBIL post-login", "Lost to Competitor Rate"], "Count": [int(1500*scale), int(800*scale)], "Severity": ["Critical (Screening Failure)", "High (Pricing Issue)"]})

    return summary, df_mom, df_aging, df_health, df_lost, ano_t1, ano_t2, ano_t3

@st.cache_data
def get_frt_data(source, scale):
    np.random.seed(seed_map.get(source, 42))
    df_frt = pd.DataFrame({
        "Response Time": ["< 1 hr", "1 - 6 hrs", "6 - 24 hrs", "24+ hrs"],
        "Volume": (np.array([15000, 35000, 25000, 10000]) * scale).astype(int),
        "Conv (%)": [65.4, 42.1, 28.5, 11.2]
    })
    return np.random.uniform(3.5, 6.0), df_frt

@st.cache_data
def get_t2_specifics(source, scale):
    np.random.seed(seed_map.get(source, 42))
    # Doable vs Shared
    vol_bp = int(21500 * scale)
    missed = int(vol_bp * np.random.uniform(5.8, 6.5)) - int(vol_bp * np.random.uniform(3.4, 4.2))
    df_wf = pd.DataFrame({"Metric": ["Max Potential", "Unutilized", "Actually Shared"], "Value": [int(vol_bp * 6.0), -missed, int(vol_bp * 3.8)]})
    df_buckets = pd.DataFrame({"Bucket": ["Exactly 3", "4 to 5", "6 to 7", "8+"], "Vol": (np.array([4500, 3200, 1500, 800]) * (vol_bp/10000)).astype(int)})
    # Profile Completion
    comp_share, comp_login = np.random.uniform(45, 55), np.random.uniform(85, 96)
    # Ready to Push Pipeline
    df_ready = pd.DataFrame({"Aging": ["0-3 Days", "4-7 Days", "8+ Days (Critical)"], "Vol": (np.array([1200, 700, 300]) * scale).astype(int)})
    return df_wf, df_buckets, comp_share, comp_login, df_ready

@st.cache_data
def get_rm_and_ics(source, scale):
    np.random.seed(seed_map.get(source, 42))
    rms = ["Rahul Desai", "Priya Sharma", "Amit Singh", "Sneha", "Vikram", "Neha", "Rohit", "Pooja", "Karan", "Anjali"]
    shared = np.random.randint(int(30*scale*5), int(150*scale*5), 10)
    logins = (shared * np.random.uniform(0.3, 0.7, 10)).astype(int)
    sanctions = (logins * np.random.uniform(0.4, 0.8, 10)).astype(int)
    pfs = (sanctions * np.random.uniform(0.5, 0.9, 10)).astype(int)
    df_rm = pd.DataFrame({"RM Name": rms, "Shared (BP)": shared, "Logins": logins, "Sanctions": sanctions, "PFs (Won)": pfs})
    df_rm["BP to Login (%)"] = (df_rm["Logins"]/df_rm["Shared (BP)"]*100).round(1)
    df_rm["Login to Sanc (%)"] = (df_rm["Sanctions"]/df_rm["Logins"]*100).round(1)
    df_rm["Sanc to PF (%)"] = (df_rm["PFs (Won)"]/df_rm["Sanctions"]*100).round(1)
    
    weeks = [f"week{i}" for i in range(20)]
    tps_data, ics_data = [], []
    for rm in rms:
        t, i = np.random.uniform(0.5, 3.5, 20).round(2), np.random.uniform(0.5, 1.5, 20).round(2)
        tps_data.append([rm, np.mean(t).round(2)] + t.tolist())
        ics_data.append([rm, np.mean(i).round(2)] + i.tolist())
    df_tps = pd.DataFrame(tps_data, columns=['RM', 'overalltps'] + weeks)
    df_ics = pd.DataFrame(ics_data, columns=['RM', 'overallics'] + weeks)
    return df_rm.sort_values(by="PFs (Won)", ascending=False), df_tps, df_ics

# Load Data
summary, df_mom, df_aging, df_health, df_lost, ano_t1, ano_t2, ano_t3 = get_master_pipeline(selected_source, master_scale)
sys_avg_frt, df_frt = get_frt_data(selected_source, master_scale)
df_wf, df_buckets, comp_share, comp_login, df_ready = get_t2_specifics(selected_source, master_scale)
df_rm, df_tps, df_ics = get_rm_and_ics(selected_source, master_scale)

# ==========================================
# 4. MODULAR UI COMPONENTS
# ==========================================

# Trick to ensure mathematically unique keys across all tabs without changing your tab code
UI_COUNTER = 0
def get_uid(base_name):
    global UI_COUNTER
    UI_COUNTER += 1
    return f"{base_name}_{UI_COUNTER}"

def ui_snapshot(keys, titles):
    cols = st.columns(len(keys))
    for col, key, title in zip(cols, keys, titles):
        curr, lytd, tgt = summary[key]["curr"], summary[key]["lytd"], summary[key]["target"]
        delta = ((curr - lytd) / lytd) * 100 if lytd else 0
        with col:
            st.markdown('<div class="macro-metric">', unsafe_allow_html=True)
            st.metric(title, f"{curr:,}", f"{delta:+.1f}% vs LYTD")
            st.progress(min(curr / tgt, 1.0))
            st.caption(f"🎯 **{(curr/tgt)*100:.1f}%** of Target")

def ui_mom_variance(keys, titles, colors):
    cols = st.columns(len(keys))
    for col, key, title, color in zip(cols, keys, titles, colors):
        with col:
            fig = px.line(df_mom, x="Month", y=key, color="Year", markers=True, color_discrete_sequence=["#aec7e8", color], title=title)
            fig.update_layout(template=plotly_theme, margin=dict(t=30, b=0, l=0, r=0), height=250, yaxis_title=None, xaxis_title=None, legend=dict(orientation="h", y=-0.3, title=None))
            # Notice the get_uid() wrap!
            st.plotly_chart(fig, use_container_width=True, key=get_uid(f"var_{key}"))

def ui_mom_conversion(keys, titles, colors):
    cols = st.columns(len(keys))
    for col, key, title, color in zip(cols, keys, titles, colors):
        with col:
            fig = px.line(df_mom, x="Month", y=key, color="Year", color_discrete_map={"LYTD": "#7f8c8d", "Current": color}, title=title)
            fig.update_traces(mode="lines+markers", line=dict(width=3), marker=dict(size=8, symbol="hexagram"))
            fig.update_layout(template=plotly_theme, margin=dict(t=30, b=0, l=0, r=0), height=250, yaxis=dict(title=None, ticksuffix="%"), xaxis=dict(title=None, showgrid=False), legend=dict(orientation="h", y=-0.3, title=None), hovermode="x unified")
            # Notice the get_uid() wrap!
            st.plotly_chart(fig, use_container_width=True, key=get_uid(f"conv_{key}"))

def ui_html_funnel(keys, stages, colors):
    vols = [summary[k]["curr"] for k in keys]
    lytd_vols = [summary[k]["lytd"] for k in keys]
    
    html = f"""<div style="display: flex; align-items: center; justify-content: space-between; width: 100%; padding: 20px 0; font-family: sans-serif;">"""
    for i in range(len(stages)):
        html += f"""
        <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
            <div style="background-color: {colors[i]}; color: white; height: {100 - i*10}px; width: 100%; display: flex; align-items: center; justify-content: center; font-size: {26 - i*2}px; font-weight: bold; border-radius: 4px; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">{vols[i]:,}</div>
            <div style="margin-top: 15px; font-size: 16px; font-weight: bold; color: {text_color};">{stages[i]}</div>
        </div>"""
        
        if i < len(stages) - 1:
            conv = int(vols[i+1]/vols[i]*100) if vols[i] else 0
            lytd_conv = int(lytd_vols[i+1]/lytd_vols[i]*100) if lytd_vols[i] else 0
            html += f"""
            <div style="flex: 0.35; display: flex; flex-direction: column; align-items: center; margin-top: -30px;">
                <div style="font-size: 24px; font-weight: bold; color: #2ecc71;">{conv}% ➔</div>
                <div style="background-color: {metric_bg}; padding: 6px 10px; border-radius: 6px; border: 1px solid {grid_color}; margin-top: 8px; text-align: center;">
                    <div style="font-size: 11px; color: {text_color};"><b>LYTD:</b> <span style="color: #7f8c8d;">{lytd_conv}%</span></div>
                </div>
            </div>"""
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def ui_active_aging(keys):
    df = df_aging[df_aging["Stage"].isin(keys)]
    fig = px.bar(df, y="Stage", x="Active Leads", color="Aging Bucket", orientation='h', color_discrete_map={"0-7 Days": "#2ca02c", "8-14 Days": "#f39c12", "15-21 Days": "#e67e22", "21+ Days": "#e74c3c"}, category_orders={"Aging Bucket": ["0-7 Days", "8-14 Days", "15-21 Days", "21+ Days"]})
    fig.update_layout(template=plotly_theme, height=200, barmode="stack", margin=dict(t=10, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.4, title=None), yaxis_title=None, xaxis_title=None)
    st.plotly_chart(fig, use_container_width=True, key=get_uid("aging"))

def ui_engagement_health(keys):
    df = df_health[df_health["Stage"].isin(keys)]
    col_ltb, col_lcb = st.columns(2)
    c_map = {"LTB: 0-3 Days (Hot)": "#2ecc71", "LCB: 0-3 Days (Hot)": "#2ecc71", "LTB: 4-7 Days (Warm)": "#f39c12", "LCB: 4-7 Days (Warm)": "#f39c12", "LTB: 8+ Days (Zombie)": "#e74c3c", "LCB: 8+ Days (Zombie)": "#e74c3c"}
    
    with col_ltb:
        st.write("**RM Effort (LTB Bucket)**")
        df_l = df.melt(id_vars="Stage", value_vars=["LTB: 0-3 Days (Hot)", "LTB: 4-7 Days (Warm)", "LTB: 8+ Days (Zombie)"], var_name="Health", value_name="Leads")
        fig = px.bar(df_l, y="Stage", x="Leads", color="Health", orientation="h", color_discrete_map=c_map, text_auto=".2s")
        fig.update_layout(template=plotly_theme, height=200, barmode="stack", margin=dict(t=0, b=0, l=0, r=0), yaxis=dict(autorange="reversed", title=None), xaxis=dict(showticklabels=False, title=None), legend=dict(orientation="h", y=-0.4, title=None))
        st.plotly_chart(fig, use_container_width=True, key=get_uid("ltb"))

    with col_lcb:
        st.write("**Student Reality (LCB Bucket)**")
        df_c = df.melt(id_vars="Stage", value_vars=["LCB: 0-3 Days (Hot)", "LCB: 4-7 Days (Warm)", "LCB: 8+ Days (Zombie)"], var_name="Health", value_name="Leads")
        fig = px.bar(df_c, y="Stage", x="Leads", color="Health", orientation="h", color_discrete_map=c_map, text_auto=".2s")
        fig.update_layout(template=plotly_theme, height=200, barmode="stack", margin=dict(t=0, b=0, l=0, r=0), yaxis=dict(autorange="reversed", title=None, showticklabels=False), xaxis=dict(showticklabels=False, title=None), legend=dict(orientation="h", y=-0.4, title=None))
        st.plotly_chart(fig, use_container_width=True, key=get_uid("lcb"))

def ui_lost_analysis(keys, anomalies):
    df = df_lost[df_lost["Stage"].isin(keys)]
    col_tree, col_flags = st.columns([1.3, 1])
    
    with col_tree:
        st.write("**Top Drop Reasons by Stage**")
        fig_tree = px.treemap(df, path=["Stage", "Reason"], values="Count", color="Count", color_continuous_scale="Reds")
        fig_tree.update_traces(textinfo="label+value+percent parent", textfont=dict(size=14, color="white"))
        fig_tree.update_layout(template=plotly_theme, height=280, margin=dict(t=0, b=0, l=0, r=0), coloraxis_showscale=False)
        st.plotly_chart(fig_tree, use_container_width=True, key=get_uid("tree"))

    with col_flags:
        st.write("**🚨 Automated Anomaly Detection**")
        fig_flags = px.bar(anomalies.sort_values(by="Count", ascending=True), x="Count", y="Flag Type", color="Severity", orientation="h", text_auto=".2s", color_discrete_map={"Critical (Bandwidth Waste)": "#c0392b", "High (SLA Evasion)": "#e74c3c", "Medium (Data Loss)": "#f39c12", "High (Ghosting)": "#e67e22", "Critical (Screening Failure)": "#8e44ad", "High (Pricing Issue)": "#d35400"})
        fig_flags.update_layout(template=plotly_theme, height=250, margin=dict(t=0, b=0, l=0, r=0), yaxis_title=None, xaxis_title=None, legend=dict(orientation="h", y=-0.2, title=None))
        st.plotly_chart(fig_flags, use_container_width=True, key=get_uid("flags"))

# ==========================================
# 5. TAB IMPLEMENTATION
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🚀 1. Lead Capture to R2S", 
    "🏦 2. R2S to Login", 
    "💰 3. Login to PF", 
    "🧑‍💼 4. RM Performance", 
    "🧠 5. Intelligent Metrics"
])

# ----------------- TAB 1: CAPTURE TO R2S -----------------
with tab1:
    st.subheader(f"1. Executive Snapshot (Pre-Sharing Pipeline)")
    ui_snapshot(["Capture", "App Start", "R2S"], ["Lead Capture", "App Start", "Ready to Share (R2S)"])
    st.divider()
    
    st.subheader("2. MoM Volume Variance")
    ui_mom_variance(["Capture", "App Start", "R2S"], ["Capture Volume", "App Start Volume", "R2S Volume"], ["#2c3e50", "#34495e", "#7f8c8d"])
    st.divider()
    
    st.subheader("3. MoM Conversion Efficiency")
    ui_mom_conversion(["Cap ➔ App (%)", "App ➔ R2S (%)"], ["Capture ➔ App Start", "App Start ➔ R2S"], ["#e67e22", "#9b59b6"])
    st.divider()
    
    st.subheader("4. Pre-Sharing Trajectory Funnel")
    ui_html_funnel(["Capture", "App Start", "R2S"], ["Lead Capture", "App Start", "Ready to Share"], ["#2c3e50", "#34495e", "#7f8c8d"])
    st.divider()
    
    st.subheader("5. Active Pipeline Aging & Engagement Health")
    ui_active_aging(["Capture", "App Start", "R2S"])
    st.write("---")
    ui_engagement_health(["Capture", "App Start", "R2S"])
    st.divider()
    
    st.subheader("6. Speed-to-Lead (First Response Time SLA)")
    c1, c2 = st.columns([1, 2])
    with c1:
        fig_g = go.Figure(go.Indicator(mode="gauge+number", value=sys_avg_frt, title={'text': "Avg Hrs to Dial", 'font': {'size': 14}}, number={'suffix': "h"}, gauge={'axis': {'range': [0, 24]}, 'bar': {'color': "#3498db"}, 'steps': [{'range': [0, 2], 'color': 'rgba(46,204,113,0.3)'}, {'range': [6, 24], 'color': 'rgba(231,76,60,0.3)'}], 'threshold': {'line': {'color': "red", 'width': 4}, 'value': 2}}))
        fig_g.update_layout(template=plotly_theme, height=250, margin=dict(t=30, b=0, l=10, r=10))
        st.plotly_chart(fig_g, use_container_width=True)
    with c2:
        fig_d = go.Figure()
        fig_d.add_trace(go.Bar(x=df_frt["Response Time"], y=df_frt["Volume"], name="Volume", marker_color="#34495e"))
        fig_d.add_trace(go.Scatter(x=df_frt["Response Time"], y=df_frt["Conv (%)"], name="Conv %", yaxis="y2", mode="lines+markers+text", text=df_frt["Conv (%)"].astype(str)+"%", textposition="top center", line=dict(color="#e67e22", width=4)))
        fig_d.update_layout(template=plotly_theme, height=250, margin=dict(t=10, b=0, l=0, r=0), yaxis2=dict(overlaying="y", side="right", showgrid=False), legend=dict(orientation="h", y=-0.3, title=None))
        st.plotly_chart(fig_d, use_container_width=True)
    st.divider()
    
    st.subheader("7. Lost Lead Intelligence (Pre-Sharing Drops)")
    ui_lost_analysis(["Capture", "App Start"], ano_t1)

# ----------------- TAB 2: R2S TO LOGIN -----------------
with tab2:
    st.subheader(f"1. Executive Snapshot (Bank Submission Pipeline)")
    ui_snapshot(["R2S", "Shared", "Login"], ["Ready to Share", "Bank Prospects (Shared)", "Logins"])
    st.divider()
    
    st.subheader("2. MoM Volume Variance")
    ui_mom_variance(["R2S", "Shared", "Login"], ["R2S Volume", "Shared Volume", "Login Volume"], ["#7f8c8d", "#4a47d3", "#605ee0"])
    st.divider()
    
    st.subheader("3. MoM Conversion Efficiency")
    ui_mom_conversion(["R2S ➔ Shr (%)", "Shr ➔ Log (%)"], ["R2S ➔ Shared", "Shared ➔ Login"], ["#3498db", "#2ecc71"])
    st.divider()
    
    st.subheader("4. Bank Submission Trajectory Funnel")
    ui_html_funnel(["R2S", "Shared", "Login"], ["Ready to Share", "Shared (BP)", "Logins"], ["#7f8c8d", "#4a47d3", "#605ee0"])
    st.divider()
    
    st.subheader("5. Active Pipeline Aging & Engagement Health")
    ui_active_aging(["R2S", "Shared"])
    st.write("---")
    ui_engagement_health(["R2S", "Shared"])
    st.divider()

    st.subheader("6. The 'Left on the Table' Analysis (Doable vs. Shared)")
    cd1, cd2 = st.columns(2)
    with cd1:
        st.write("**The 'Bare Minimum' Syndrome**")
        fig_dn = px.pie(df_buckets, names="Bucket", values="Vol", hole=0.6, color="Bucket", color_discrete_map={"Exactly 3": "#e74c3c", "4 to 5": "#f39c12", "6 to 7": "#3498db", "8+": "#2ecc71"})
        fig_dn.update_layout(template=plotly_theme, height=250, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_dn, use_container_width=True)
    with cd2:
        st.write("**System-Wide Missed Opportunities**")
        fig_wf = go.Figure(go.Waterfall(x=df_wf["Metric"], y=df_wf["Value"], text=[f"{v:,}" for v in df_wf['Value'].abs()], textposition="outside", decreasing={"marker": {"color": "#e74c3c"}}, totals={"marker": {"color": "#3498db"}}, increasing={"marker": {"color": "#7f8c8d"}}))
        fig_wf.update_layout(template=plotly_theme, height=250, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_wf, use_container_width=True)
    st.divider()
    
    st.subheader("7. Profile Completion (Time of Share vs. Login)")
    cv1, cv2 = st.columns(2)
    with cv1:
        st.write("**Completion at Time of Sharing (Day 0)**")
        fig_s = go.Figure(go.Indicator(mode="gauge+number", value=comp_share, number={'suffix': "%"}, gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#3498db"}}))
        fig_s.update_layout(template=plotly_theme, height=220, margin=dict(t=0, b=0, l=10, r=10))
        st.plotly_chart(fig_s, use_container_width=True)
    with cv2:
        st.write("**Completion at Time of Login**")
        fig_l = go.Figure(go.Indicator(mode="gauge+number", value=comp_login, number={'suffix': "%"}, gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#2ecc71"}}))
        fig_l.update_layout(template=plotly_theme, height=220, margin=dict(t=0, b=0, l=10, r=10))
        st.plotly_chart(fig_l, use_container_width=True)
    st.divider()

    st.subheader("8. The 'Ready to Push' Pipeline (Unlogged + Highly Complete)")
    st.caption("Active leads sitting in 'Shared' status that have >70% profile completion and are primed for Login.")
    cr1, cr2 = st.columns([1, 2])
    with cr1:
        st.markdown('<div class="macro-metric">', unsafe_allow_html=True)
        st.metric("Primed for Login", f"{df_ready['Vol'].sum():,}", "High Priority Pipeline")
    with cr2:
        fig_r = px.bar(df_ready, x="Vol", y="Aging", orientation='h', color="Aging", text_auto=".2s", color_discrete_map={"0-3 Days": "#2ecc71", "4-7 Days": "#f39c12", "8+ Days (Critical)": "#e74c3c"})
        fig_r.update_layout(template=plotly_theme, height=180, margin=dict(t=0, b=0, l=0, r=0), showlegend=False, yaxis_title=None, xaxis_title=None)
        st.plotly_chart(fig_r, use_container_width=True)
    st.divider()
    
    st.subheader("9. Lost Lead Intelligence (Bank Submission Drops)")
    ui_lost_analysis(["R2S", "Shared"], ano_t2)

# ----------------- TAB 3: LOGIN TO PF -----------------
with tab3:
    st.subheader(f"1. Executive Snapshot (Bank Processing Pipeline)")
    ui_snapshot(["Login", "Sanction", "PF"], ["Logins", "Sanctions", "PFs (Won)"])
    st.divider()
    
    st.subheader("2. MoM Volume Variance")
    ui_mom_variance(["Login", "Sanction", "PF"], ["Login Volume", "Sanction Volume", "PF Volume"], ["#605ee0", "#7c7bee", "#9c9cf5"])
    st.divider()
    
    st.subheader("3. MoM Conversion Efficiency")
    ui_mom_conversion(["Log ➔ San (%)", "San ➔ PF (%)"], ["Login ➔ Sanction", "Sanction ➔ PF"], ["#f39c12", "#2ecc71"])
    st.divider()
    
    st.subheader("4. Bank Processing Trajectory Funnel")
    ui_html_funnel(["Login", "Sanction", "PF"], ["Logins", "Sanctions", "PFs (Won)"], ["#605ee0", "#7c7bee", "#9c9cf5"])
    st.divider()
    
    st.subheader("5. Active Pipeline Aging & Engagement Health")
    ui_active_aging(["Login", "Sanction"])
    st.write("---")
    ui_engagement_health(["Login", "Sanction"])
    st.divider()
    
    st.subheader("6. Lost Lead Intelligence (Late-Stage Processing Drops)")
    ui_lost_analysis(["Login", "Sanction"], ano_t3)

# ----------------- TAB 4: RM PERFORMANCE -----------------
with tab4:
    st.subheader("1. The Apex Performers (Volume Leaderboard)")
    df_rm_m = df_rm.melt(id_vars="RM Name", value_vars=["Shared (BP)", "Logins", "Sanctions", "PFs (Won)"], var_name="Stage", value_name="Vol")
    fig_rmv = px.bar(df_rm_m, x="RM Name", y="Vol", color="Stage", barmode="group", color_discrete_map={"Shared (BP)": "#4a47d3", "Logins": "#605ee0", "Sanctions": "#7c7bee", "PFs (Won)": "#9c9cf5"})
    fig_rmv.update_layout(template=plotly_theme, height=350, margin=dict(t=10, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.2, title=None), xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig_rmv, use_container_width=True)
    st.divider()
    
    st.subheader("2. Conversion Leaks (The Bottom 5 RMs)")
    cb1, cb2, cb3 = st.columns(3)
    def plot_bot5(df, col, title, c):
        f = px.bar(df.nsmallest(5, col).sort_values(col, ascending=False), y="RM Name", x=col, orientation='h', title=title, text_auto='.1f', color_discrete_sequence=[c])
        f.update_layout(template=plotly_theme, height=250, margin=dict(t=30, b=0, l=0, r=10), yaxis_title=None, xaxis_title=None, xaxis=dict(showticklabels=False))
        return f
    with cb1: st.plotly_chart(plot_bot5(df_rm, "BP to Login (%)", "Shared ➔ Login (%)", "#e74c3c"), use_container_width=True)
    with cb2: st.plotly_chart(plot_bot5(df_rm, "Login to Sanc (%)", "Login ➔ Sanction (%)", "#e67e22"), use_container_width=True)
    with cb3: st.plotly_chart(plot_bot5(df_rm, "Sanc to PF (%)", "Sanction ➔ PF (%)", "#c0392b"), use_container_width=True)

# ----------------- TAB 5: INTELLIGENT METRICS -----------------
with tab5:
    metric_focus = st.radio("Select Metric to Analyze:", ["📈 ICS (Inquiry Conv Score)", "⏱️ TPS (Time Per Stage)"], horizontal=True)
    st.divider()
    df_base = df_ics if "ICS" in metric_focus else df_tps
    df_m = df_base.melt(id_vars="RM", value_vars=[f"week{i}" for i in range(20)], var_name="Wk", value_name="Val")
    df_m["Wk_Num"] = df_m["Wk"].str.replace('week','').astype(int)
    
    st.subheader(f"1. Overall Standings Matrix")
    fig_mat = px.imshow(df_m.pivot(index="RM", columns="Wk_Num", values="Val"), aspect="auto", color_continuous_scale="Tealgrn" if "ICS" in metric_focus else "OrRd")
    fig_mat.update_layout(template=plotly_theme, height=400, margin=dict(t=10, b=20, l=0, r=0))
    st.plotly_chart(fig_mat, use_container_width=True)
