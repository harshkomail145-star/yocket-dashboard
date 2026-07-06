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
# 2. MOCK DATA GENERATION ENGINE
# ==========================================
@st.cache_data
def get_lytd_data():
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
    df_vol = pd.DataFrame({
        "Month": months * 2,
        "Year": ["LYTD"] * 7 + ["Current"] * 7,
        "BP": [3000, 3200, 3500, 3100, 4000, 4500, 4800,   3300, 3100, 3800, 3400, 4300, 4800, 5200],
        "Logins": [600, 650, 700, 620, 800, 900, 960,      660, 610, 780, 680, 860, 980, 1050],
        "Sanctions": [300, 330, 360, 310, 420, 470, 500,   330, 300, 390, 350, 440, 500, 530],
        "PFs": [180, 200, 220, 190, 260, 290, 310,         200, 180, 240, 220, 280, 320, 340]
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
    return df_vol, df_conv, df_multi, df_tat

@st.cache_data
def get_current_funnel_data():
    df_funnel = pd.DataFrame({
        "Stage": ["1. Shared (BP)", "2. Logins", "3. Sanctions", "4. PFs (Won)"],
        "Progressed": [14200, 7668, 4600, 4600],
        "Active": [4200, 2800, 1100, 0],         
        "Lost": [3100, 3732, 1968, 0]            
    })
    df_aging = pd.DataFrame({
        "Stage": ["Shared (BP)"]*4 + ["Logins"]*4 + ["Sanctions"]*4,
        "Aging Bucket": ["0-7 Days", "8-14 Days", "15-21 Days", "21+ Days"] * 3,
        "Active Leads": [2000, 1400, 600, 200, 1200, 1000, 450, 150, 500, 400, 150, 50]
    })
    df_lost_shared = pd.DataFrame({"Reason": ["Unresponsive", "Low Intent", "Already Applied", "Ineligible"], "Count": [1200, 850, 600, 450]}).sort_values('Count') 
    df_lost_login = pd.DataFrame({"Reason": ["Low CIBIL", "Low Co-app Income", "Missing Docs", "Property Issue"], "Count": [1500, 1100, 732, 400]}).sort_values('Count')
    df_lost_sanction = pd.DataFrame({"Reason": ["Better Rate Elsewhere", "Visa Rejection", "Deferred", "Competitor Matched"], "Count": [800, 650, 318, 200]}).sort_values('Count')
    df_ltb_lcb = pd.DataFrame({
        "Stage_Metric": ["1. BP - LTB (Touched)", "1. BP - LCB (Connected)", "2. Logins - LTB (Touched)", "2. Logins - LCB (Connected)", "3. Sanctions - LTB (Touched)", "3. Sanctions - LCB (Connected)"],
        "0-3 Days (Good)": [1800, 900, 1300, 750, 600, 400],
        "4-7 Days (Warm)": [1500, 1100, 900, 1000, 300, 450],
        "8+ Days (Terrible)": [900, 2200, 600, 1050, 200, 250]
    })
    return df_funnel, df_aging, df_lost_shared, df_lost_login, df_lost_sanction, df_ltb_lcb

@st.cache_data
def get_rm_data():
    np.random.seed(42) # For reproducible mock data
    rms = ["Rahul Desai", "Priya Sharma", "Amit Singh", "Sneha Gupta", "Vikram Patel", "Neha Verma", "Rohit Kumar", "Pooja Reddy", "Karan Malhotra", "Anjali Joshi"]
    
    shared = np.random.randint(150, 400, 10)
    logins = (shared * np.random.uniform(0.15, 0.55, 10)).astype(int)
    sanctions = (logins * np.random.uniform(0.3, 0.75, 10)).astype(int)
    pfs = (sanctions * np.random.uniform(0.4, 0.85, 10)).astype(int)
    
    # TAT Data (Average Days)
    tat_bp_login = np.random.uniform(2.0, 8.5, 10).round(1)
    tat_login_sanc = np.random.uniform(3.0, 11.0, 10).round(1)
    tat_sanc_pf = np.random.uniform(1.5, 7.0, 10).round(1)

    # Active Aging Data
    age_bp = np.random.uniform(3.0, 16.0, 10).round(1)
    age_login = np.random.uniform(5.0, 19.0, 10).round(1)
    age_sanc = np.random.uniform(2.0, 14.0, 10).round(1)

    # Stale Engagement Volume
    ltb_stale = np.random.randint(5, 50, 10)
    lcb_stale = np.random.randint(15, 80, 10)
    
    # NEW: Query Resolution Data
    queries_raised = np.random.randint(40, 150, 10)
    queries_resolved = (queries_raised * np.random.uniform(0.3, 0.9, 10)).astype(int)
    unresolved = queries_raised - queries_resolved
    age_unresolved = np.random.uniform(2.0, 14.0, 10).round(1) # How old the pending queries are
    
    df_rm = pd.DataFrame({
        "RM Name": rms,
        "Shared (BP)": shared, "Logins": logins, "Sanctions": sanctions, "PFs (Won)": pfs,
        "BP to Login (%)": (logins / shared * 100).round(1),
        "Login to Sanction (%)": (sanctions / logins * 100).round(1),
        "Sanction to PF (%)": (pfs / sanctions * 100).round(1),
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

df_vol, df_conv, df_multi, df_tat = get_lytd_data()
df_funnel, df_aging, df_lost_shared, df_lost_login, df_lost_sanction, df_ltb_lcb = get_current_funnel_data()
df_rm = get_rm_data()

# ==========================================
# 3. APP HEADER & TAB DEFINITION
# ==========================================
st.title("🎯 Yocket BOFU Operations Pulse")
st.caption("Executive Dashboard | Live Trajectory, Funnel Tracking & RM Performance")
st.divider()

tab1, tab2, tab3 = st.tabs([
    "📊 1. LYTD & Current Pipeline", 
    "🧑‍💼 2. RM Performance & SLAs", 
    "🤝 3. Partner Insights (Pending)"
])

# ==========================================
# 4. TAB 1: LYTD PERFORMANCE & CURRENT PIPELINE
# ==========================================
with tab1:
    st.subheader("1. Executive Snapshot (Current vs LYTD)")
    col1, col2, col3, col4 = st.columns(4)

    target_bp, target_logins, target_sanctions, target_pfs = 30000, 16000, 10000, 6000
    curr_bp, curr_logins, curr_sanctions, curr_pfs = 21500, 14200, 7668, 4600

    with col1:
        st.markdown('<div class="macro-metric">', unsafe_allow_html=True)
        st.metric("BP / Shared", f"{curr_bp:,}", "+7.5% vs LYTD")
        st.progress(min(curr_bp / target_bp, 1.0))
        st.caption(f"🎯 **{(curr_bp/target_bp)*100:.1f}%** of Target")

    with col2:
        st.metric("Logins", f"{curr_logins:,}", "+5.2% vs LYTD")
        st.progress(min(curr_logins / target_logins, 1.0))
        st.caption(f"🎯 **{(curr_logins/target_logins)*100:.1f}%** of Target")

    with col3:
        st.metric("Sanctions", f"{curr_sanctions:,}", "+4.8% vs LYTD")
        st.progress(min(curr_sanctions / target_sanctions, 1.0))
        st.caption(f"🎯 **{(curr_sanctions/target_sanctions)*100:.1f}%** of Target")

    with col4:
        st.metric("PFs", f"{curr_pfs:,}", "+7.9% vs LYTD")
        st.progress(min(curr_pfs / target_pfs, 1.0))
        st.caption(f"🎯 **{(curr_pfs/target_pfs)*100:.1f}%** of Target")

    st.divider()
    st.subheader("2. Month-on-Month Volume Variance")
    vol_metric = st.selectbox("Select Metric to View Variance:", ["BP", "Logins", "Sanctions", "PFs"], index=1)
    
    fig_vol = px.bar(df_vol, x="Month", y=vol_metric, color="Year", barmode="group", color_discrete_sequence=["#aec7e8", "#1f77b4"])
    fig_vol.update_layout(template=plotly_theme, margin=dict(t=20, b=0, l=0, r=0), height=300, legend=dict(orientation="h", y=-0.2, title=None))
    st.plotly_chart(fig_vol, use_container_width=True)

    st.divider()
    col_multi, col_tat = st.columns([1.2, 1])
    with col_multi:
        st.subheader("3. Multi-Rate Comparison")
        df_multi_melted = df_multi.melt(id_vars=["Stage", "Target"], value_vars=["LYTD_Ratio", "Current_Ratio"], var_name="Year", value_name="Ratio").replace({"LYTD_Ratio": "LYTD", "Current_Ratio": "Current"})
        fig_multi = px.bar(df_multi_melted, x="Stage", y="Ratio", color="Year", barmode="group", color_discrete_sequence=["#aec7e8", "#2ca02c"], text_auto='.2f')
        for i, row in df_multi.iterrows():
            fig_multi.add_shape(type="line", x0=i-0.4, x1=i+0.4, y0=row["Target"], y1=row["Target"], line=dict(color="red", width=2, dash="dash"))
        fig_multi.update_layout(template=plotly_theme, height=300, margin=dict(t=20, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.2, title=None))
        st.plotly_chart(fig_multi, use_container_width=True)

    with col_tat:
        st.subheader("4. TAT Variance (Days)")
        st.write("##")
        for _, row in df_tat.iterrows():
            st.metric(f"⏳ {row['Conversion Stage']}", f"{row['Current_Days']} Days", f"{row['Current_Days'] - row['LYTD_Days']:+.1f} Days vs LYTD", delta_color="inverse")

    st.divider()
    st.write("## Current Year Funnel Intelligence")
    col_funnel, col_aging = st.columns([1.5, 1])
    
    with col_funnel:
        st.subheader("5. Conversion Cohort Status")
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
        st.subheader("6. Active Pipeline Aging")
        fig_aging = px.bar(df_aging, y="Stage", x="Active Leads", color="Aging Bucket", orientation='h', 
                           color_discrete_map={"0-7 Days": "#2ca02c", "8-14 Days": "#ffc107", "15-21 Days": "#ff7f0e", "21+ Days": "#d62728"},
                           category_orders={"Aging Bucket": ["0-7 Days", "8-14 Days", "15-21 Days", "21+ Days"]})
        fig_aging.update_layout(template=plotly_theme, height=300, barmode="stack", margin=dict(t=20, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.3, title=None))
        st.plotly_chart(fig_aging, use_container_width=True)

    st.write("##")
    st.subheader("7. Lead Engagement: LTB & LCB Health")
    df_ltb_melted = df_ltb_lcb.melt(id_vars="Stage_Metric", var_name="Health Status", value_name="Leads")
    fig_ltb = px.bar(df_ltb_melted, y="Stage_Metric", x="Leads", color="Health Status", orientation='h', 
                     color_discrete_map={"0-3 Days (Good)": "#2ecc71", "4-7 Days (Warm)": "#f39c12", "8+ Days (Terrible)": "#e74c3c"}, text_auto='.2s')
    fig_ltb.update_layout(template=plotly_theme, height=300, barmode="stack", margin=dict(t=20, b=0, l=0, r=0), yaxis={'categoryorder': 'category descending', 'title': None}, xaxis={'title': None, 'showgrid': False, 'showticklabels': False}, legend=dict(orientation="h", y=-0.15, title=None))
    fig_ltb.update_traces(textposition="inside", textfont_size=13, textangle=0)
    st.plotly_chart(fig_ltb, use_container_width=True)
    # ==========================================
    # 8. LOST PIPELINE DIAGNOSTICS
    # ==========================================
    st.divider()
    st.subheader("8. Lost Pipeline Diagnostics")
    st.caption("Top reasons for dropped leads at each major conversion stage, ranked highest to lowest.")
    
    col_lost1, col_lost2, col_lost3 = st.columns(3)
    
    # Helper function to keep chart styling consistent and clean
    def plot_lost_reasons(df, title, color):
        fig = px.bar(
            df, y="Reason", x="Count", orientation='h', title=title, 
            color_discrete_sequence=[color], text_auto='.2s'
        )
        fig.update_layout(
            template=plotly_theme, 
            height=280, 
            margin=dict(t=40, b=0, l=0, r=20), 
            yaxis_title=None, 
            xaxis_title=None,
            xaxis=dict(showgrid=False, showticklabels=False) # Hide X axis numbers for clean look
        )
        
        # Force text color to adapt to dark/light mode so it never disappears
        fig.update_traces(textposition="outside", textfont_size=12, cliponaxis=False, textfont=dict(color=text_color))
        return fig
    
    with col_lost1:
        st.plotly_chart(plot_lost_reasons(df_lost_shared, "Shared ➔ Lost", "#e74c3c"), use_container_width=True)
    with col_lost2:
        st.plotly_chart(plot_lost_reasons(df_lost_login, "Login ➔ Lost", "#e67e22"), use_container_width=True)
    with col_lost3:
        st.plotly_chart(plot_lost_reasons(df_lost_sanction, "Sanction ➔ Lost", "#c0392b"), use_container_width=True)

# ==========================================
# 5. TAB 2: RM PERFORMANCE & BOTTLENECKS
# ==========================================
with tab2:
    st.write("## 🧑‍💼 Relationship Manager Command Center")
    st.caption("Tracking individual operational volume, conversion bottlenecks, TAT delays, and SLA discipline.")
    
    # --- SECTION 1: LEADERBOARD ---
    st.subheader("1. The Apex Performers (Volume Leaderboard)")
    
    # Added "Shared (BP)" to the value_vars list
    df_rm_melted = df_rm.melt(
        id_vars="RM Name", 
        value_vars=["Shared (BP)", "Logins", "Sanctions", "PFs (Won)"], 
        var_name="Stage", 
        value_name="Volume"
    )
    
    fig_rm_vol = px.bar(
        df_rm_melted, x="RM Name", y="Volume", color="Stage", barmode="group",
        # Added a purple color for BP so it stands out from the rest of the funnel
        color_discrete_map={
            "Shared (BP)": "#8e44ad", 
            "Logins": "#1f77b4", 
            "Sanctions": "#2ca02c", 
            "PFs (Won)": "#ff9800"
        },
        text_auto='.2s'
    )
    
    fig_rm_vol.update_layout(
        template=plotly_theme, height=350, margin=dict(t=20, b=0, l=0, r=0),
        legend=dict(orientation="h", y=-0.2, title=None), xaxis_title=None, yaxis_title=None
    )
    fig_rm_vol.update_traces(textposition="outside", textfont_size=12, cliponaxis=False, textfont=dict(color=text_color))
    st.plotly_chart(fig_rm_vol, use_container_width=True)

    st.divider()

    # --- SECTION 2: CONVERSION BOTTLENECKS (BOTTOM 5) ---
    st.subheader("2. Conversion Leaks (The Bottom 5 RMs)")
    st.caption("Isolating the 5 RMs dragging down our conversion rates at each critical stage.")
    
    col_bot1, col_bot2, col_bot3 = st.columns(3)
    
    def plot_bottom_5(df, col_name, title, color):
        # Grab the 5 lowest, sort so the absolute worst is at the bottom of the chart
        df_bot = df.nsmallest(5, col_name).sort_values(col_name, ascending=False)
        fig = px.bar(df_bot, y="RM Name", x=col_name, orientation='h', title=title, text_auto='.1f', color_discrete_sequence=[color])
        fig.update_layout(
            template=plotly_theme, height=250, margin=dict(t=40, b=0, l=0, r=20),
            yaxis_title=None, xaxis_title=None, xaxis=dict(showticklabels=False, showgrid=False)
        )
        fig.update_traces(textposition="outside", textfont_size=12, cliponaxis=False, textfont=dict(color=text_color))
        return fig
        
    with col_bot1:
        st.plotly_chart(plot_bottom_5(df_rm, "BP to Login (%)", "BP ➔ Login (%)", "#e74c3c"), use_container_width=True)
    with col_bot2:
        st.plotly_chart(plot_bottom_5(df_rm, "Login to Sanction (%)", "Login ➔ Sanction (%)", "#e67e22"), use_container_width=True)
    with col_bot3:
        st.plotly_chart(plot_bottom_5(df_rm, "Sanction to PF (%)", "Sanction ➔ PF (%)", "#c0392b"), use_container_width=True)

    st.divider()

    # --- SECTION 3: TAT HEATMAP ---
    st.subheader("3. Turnaround Time (TAT) Heatmap")
    st.caption("Visually identifying which RMs process leads the slowest (Red = Slower/Terrible, Blue = Faster/Good).")
    
    # Isolate TAT columns and set RM Name as the index for the heatmap
    df_tat_heat = df_rm[["RM Name", "TAT: BP ➔ Login", "TAT: Login ➔ Sanction", "TAT: Sanction ➔ PF"]].set_index("RM Name")
    
    fig_heat = px.imshow(
        df_tat_heat, 
        text_auto=".1f", 
        aspect="auto",
        color_continuous_scale="RdBu_r", # Red to Blue reversed (Red = High numbers/Slow, Blue = Low numbers/Fast)
    )
    fig_heat.update_layout(template=plotly_theme, height=350, margin=dict(t=20, b=0, l=0, r=0), xaxis_title=None)
    st.plotly_chart(fig_heat, use_container_width=True)

    st.divider()

    # --- SECTION 4 & 5: AGING & ENGAGEMENT BLACKHOLES ---
    col_aging, col_engage = st.columns(2)
    
    with col_aging:
        st.subheader("4. Active Aging: Who holds stale leads?")
        st.caption("Average number of days an RM's active leads have been sitting in stage.")
        
        df_age_melt = df_rm.melt(id_vars="RM Name", value_vars=["Avg Age: BP", "Avg Age: Login", "Avg Age: Sanction"], var_name="Stage", value_name="Avg Days")
        
        fig_aging_rm = px.bar(
            df_age_melt, x="RM Name", y="Avg Days", color="Stage", barmode="group",
            color_discrete_map={"Avg Age: BP": "#ffc107", "Avg Age: Login": "#ff9800", "Avg Age: Sanction": "#f44336"}
        )
        fig_aging_rm.update_layout(template=plotly_theme, height=350, margin=dict(t=20, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.2, title=None), xaxis_title=None)
        st.plotly_chart(fig_aging_rm, use_container_width=True)

    with col_engage:
        st.subheader("5. Engagement Blackholes (8+ Days Uncontacted)")
        st.caption("Total count of leads sitting in LTB/LCB 'Terrible' bucket per RM.")
        
        # Sort by worst LCB offenders
        df_stale = df_rm.sort_values(by="Stale LCB (8+ Days)", ascending=False)
        df_stale_melt = df_stale.melt(id_vars="RM Name", value_vars=["Stale LTB (8+ Days)", "Stale LCB (8+ Days)"], var_name="Metric", value_name="Stale Leads")
        
        fig_stale = px.bar(
            df_stale_melt, x="RM Name", y="Stale Leads", color="Metric", barmode="group",
            color_discrete_map={"Stale LTB (8+ Days)": "#8e44ad", "Stale LCB (8+ Days)": "#c0392b"}
        )
        fig_stale.update_layout(template=plotly_theme, height=350, margin=dict(t=20, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.2, title=None), xaxis_title=None)
        st.plotly_chart(fig_stale, use_container_width=True)
        st.divider()

    # --- SECTION 6: QUERY RESOLUTION & BLOCKERS ---
    st.subheader("6. Query Resolution & Operational Blockers")
    st.caption("Tracking bank/counselor queries raised on RM files, resolution speed, and aging of unresolved blockers.")
    
    col_q1, col_q2 = st.columns(2)
    
    with col_q1:
        st.write("**Query Resolution Efficiency (%)**")
        st.caption("Percentage of raised queries successfully resolved by the RM.")
        
        # Sort by Resolution Rate (Lowest at the top to highlight bottlenecks, or highest. Let's do lowest at bottom for standard ranking)
        df_q_rate = df_rm.sort_values(by="Resolution Rate (%)", ascending=True)
        
        # Using a Red-Yellow-Green color scale (RdYlGn). High % is Green, Low % is Red.
        fig_q_rate = px.bar(
            df_q_rate, y="RM Name", x="Resolution Rate (%)", orientation="h",
            color="Resolution Rate (%)", color_continuous_scale="RdYlGn",
            text_auto=".1f"
        )
        
        fig_q_rate.update_layout(
            template=plotly_theme, height=350, margin=dict(t=20, b=0, l=0, r=0),
            yaxis_title=None, xaxis_title="Resolution %",
            coloraxis_showscale=False # Hiding the color bar to keep the UI clean
        )
        # Ensure text adapts to Dark Mode
        fig_q_rate.update_traces(textposition="outside", textfont_size=12, cliponaxis=False, textfont=dict(color=text_color))
        st.plotly_chart(fig_q_rate, use_container_width=True)

    with col_q2:
        st.write("**Unresolved Queries & Aging Heat**")
        # Sort by the most unresolved queries so the biggest blockers are at the top
        df_unresolved = df_rm.sort_values(by="Unresolved Queries", ascending=True)
        
        # Color bar based on Age (Red = old/terrible, Blue/Green = fresh/okay)
        fig_q_age = px.bar(
            df_unresolved, y="RM Name", x="Unresolved Queries", orientation="h",
            color="Avg Age: Unresolved", text="Unresolved Queries",
            color_continuous_scale="Reds", 
            labels={"Avg Age: Unresolved": "Avg Days Old"}
        )
        fig_q_age.update_layout(
            template=plotly_theme, height=350, margin=dict(t=20, b=0, l=0, r=0),
            yaxis_title=None, xaxis_title="Total Pending Queries",
            coloraxis_colorbar=dict(title="Days Old", orientation="h", y=-0.3, thickness=15)
        )
        fig_q_age.update_traces(textposition="outside", textfont_size=12, cliponaxis=False, textfont=dict(color=text_color))
        st.plotly_chart(fig_q_age, use_container_width=True)
