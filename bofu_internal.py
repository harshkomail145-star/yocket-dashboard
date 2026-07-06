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
    
    shared = np.random.randint(1200, 2800, 10)
    logins = (shared * np.random.uniform(0.4, 0.7, 10)).astype(int)
    sanctions = (logins * np.random.uniform(0.4, 0.8, 10)).astype(int)
    pfs = (sanctions * np.random.uniform(0.5, 0.9, 10)).astype(int)
    
    # SLA health per RM (percentages)
    fresh = np.random.uniform(0.3, 0.7, 10)
    warm = np.random.uniform(0.1, 0.4, 10)
    terrible = 1.0 - (fresh + warm)
    
    df_rm = pd.DataFrame({
        "RM Name": rms,
        "Shared (BP)": shared,
        "Logins": logins,
        "Sanctions": sanctions,
        "PFs (Won)": pfs,
        "Login Conv (%)": (logins / shared * 100).round(1),
        "Sanction Conv (%)": (sanctions / logins * 100).round(1),
        "PF Conv (%)": (pfs / sanctions * 100).round(1),
        "Fresh (0-3d) %": (fresh * 100).round(1),
        "Warm (4-7d) %": (warm * 100).round(1),
        "Stale (8+d) %": (terrible * 100).round(1)
    })
    return df_rm.sort_values(by="PFs (Won)", ascending=False) # Sort by best performer

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
# 5. TAB 2: RM PERFORMANCE & SLAS
# ==========================================
with tab2:
    st.write("## 🧑‍💼 Relationship Manager Command Center")
    st.caption("Tracking individual operational volume, conversion efficiency, and SLA discipline.")
    
    # --- SECTION 1: LEADERBOARD ---
    st.subheader("1. The Apex Performers (Volume Leaderboard)")
    
    df_rm_melted = df_rm.melt(id_vars="RM Name", value_vars=["Logins", "Sanctions", "PFs (Won)"], var_name="Stage", value_name="Volume")
    
    fig_rm_vol = px.bar(
        df_rm_melted, x="RM Name", y="Volume", color="Stage", barmode="group",
        color_discrete_map={"Logins": "#1f77b4", "Sanctions": "#2ca02c", "PFs (Won)": "#ff9800"},
        text_auto='.2s'
    )
    fig_rm_vol.update_layout(
        template=plotly_theme, height=350, margin=dict(t=20, b=0, l=0, r=0),
        legend=dict(orientation="h", y=-0.2, title=None), xaxis_title=None
    )
    fig_rm_vol.update_traces(textposition="outside", textfont_size=12, cliponaxis=False, textfont=dict(color=text_color))
    st.plotly_chart(fig_rm_vol, use_container_width=True)

    st.divider()

    # --- SECTION 2: EFFICIENCY vs DISCIPLINE ---
    col_eff, col_sla = st.columns(2)
    
    with col_eff:
        st.subheader("2. Efficiency Matrix (Quality vs Quantity)")
        st.caption("Top Right = High Volume & High Conversion (The Stars).")
        
        # Scatter Plot: X = Logins, Y = Sanction to PF%, Size = Total PFs
        fig_scatter = px.scatter(
            df_rm, x="Logins", y="PF Conv (%)", size="PFs (Won)", color="RM Name",
            hover_name="RM Name", text="RM Name", size_max=40
        )
        fig_scatter.update_traces(textposition='top center', textfont=dict(color=text_color))
        
        # Add quadrant crosshairs based on averages
        avg_logins = df_rm["Logins"].mean()
        avg_conv = df_rm["PF Conv (%)"].mean()
        fig_scatter.add_vline(x=avg_logins, line_width=1, line_dash="dash", line_color=text_color)
        fig_scatter.add_hline(y=avg_conv, line_width=1, line_dash="dash", line_color=text_color)
        
        fig_scatter.update_layout(template=plotly_theme, height=400, showlegend=False, margin=dict(t=20, b=0, l=0, r=0))
        st.plotly_chart(fig_scatter, use_container_width=True)

    with col_sla:
        st.subheader("3. Pipeline Discipline (SLA Adherence)")
        st.caption("What percentage of an RM's active pipeline is fresh vs rotting?")
        
        df_sla_melted = df_rm.melt(id_vars="RM Name", value_vars=["Fresh (0-3d) %", "Warm (4-7d) %", "Stale (8+d) %"], var_name="SLA Status", value_name="Percentage")
        
        fig_sla = px.bar(
            df_sla_melted, y="RM Name", x="Percentage", color="SLA Status", orientation="h", barmode="stack",
            color_discrete_map={"Fresh (0-3d) %": "#2ecc71", "Warm (4-7d) %": "#f39c12", "Stale (8+d) %": "#e74c3c"}
        )
        fig_sla.update_layout(
            template=plotly_theme, height=400, margin=dict(t=20, b=0, l=0, r=0),
            xaxis=dict(showticklabels=False, title=None), yaxis=dict(title=None, categoryorder="total ascending"),
            legend=dict(orientation="h", y=-0.15, title=None)
        )
        st.plotly_chart(fig_sla, use_container_width=True)

    st.divider()

    # --- SECTION 3: THE ULTIMATE SCORECARD ---
    st.subheader("4. The Ultimate RM Scorecard")
    st.caption("Deep-dive audit table. Click column headers to sort.")
    
    st.dataframe(
        df_rm[["RM Name", "Shared (BP)", "Logins", "Login Conv (%)", "Sanctions", "Sanction Conv (%)", "PFs (Won)", "PF Conv (%)"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "RM Name": st.column_config.TextColumn("RM Name", width="medium"),
            "Login Conv (%)": st.column_config.ProgressColumn("Login Conv (%)", format="%d%%", min_value=0, max_value=100),
            "Sanction Conv (%)": st.column_config.ProgressColumn("Sanction Conv (%)", format="%d%%", min_value=0, max_value=100),
            "PF Conv (%)": st.column_config.ProgressColumn("PF Conv (%)", format="%d%%", min_value=0, max_value=100)
        }
    )

with tab3:
    st.info("Tab 3 will be built in the next iteration.")
