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
else:
    plotly_theme = "plotly_white"
    metric_bg = "#f8f9fa"
    metric_text = "#31333F"
    grid_color = "#e5e5e5"

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
    
    # 1. MoM Volume Variance Data
    df_vol = pd.DataFrame({
        "Month": months * 2,
        "Year": ["LYTD"] * 7 + ["Current"] * 7,
        "BP": [3000, 3200, 3500, 3100, 4000, 4500, 4800,   3300, 3100, 3800, 3400, 4300, 4800, 5200],
        "Logins": [600, 650, 700, 620, 800, 900, 960,      660, 610, 780, 680, 860, 980, 1050],
        "Sanctions": [300, 330, 360, 310, 420, 470, 500,   330, 300, 390, 350, 440, 500, 530],
        "PFs": [180, 200, 220, 190, 260, 290, 310,         200, 180, 240, 220, 280, 320, 340]
    })
    
    # 2. MoM Conversion Variance Data
    df_conv = pd.DataFrame({
        "Month": df_vol["Month"],
        "Year": df_vol["Year"],
        "BP to Login (%)": (df_vol["Logins"] / df_vol["BP"] * 100).round(1),
        "Login to Sanction (%)": (df_vol["Sanctions"] / df_vol["Logins"] * 100).round(1),
        "Sanction to PF (%)": (df_vol["PFs"] / df_vol["Sanctions"] * 100).round(1)
    })
    
    # 3. Multi-Rate Comparison Data
    df_multi = pd.DataFrame({
        "Stage": ["BP / Sharing", "Logins", "Sanctions"],
        "LYTD_Ratio": [3.8, 2.0, 1.3],
        "Current_Ratio": [4.2, 1.9, 1.45],
        "Target": [4.0, 2.2, 1.7]
    })
    
    # 4. TAT (Turnaround Time) Variance Data
    df_tat = pd.DataFrame({
        "Conversion Stage": ["BP ➔ Login", "Login ➔ Sanction", "Sanction ➔ PF"],
        "LYTD_Days": [3.5, 5.0, 3.2],
        "Current_Days": [3.0, 4.2, 2.8]
    })
    
    return df_vol, df_conv, df_multi, df_tat

@st.cache_data
def get_current_funnel_data():
    # Funnel Cohort
    df_funnel = pd.DataFrame({
        "Stage": ["1. Shared (BP)", "2. Logins", "3. Sanctions", "4. PFs"],
        "Count": [21500, 14200, 7668, 4600]
    })
    
    # Active Aging Pipeline (Stuck leads not lost)
    df_aging = pd.DataFrame({
        "Stage": ["Shared (BP)", "Shared (BP)", "Shared (BP)", "Shared (BP)",
                  "Logins", "Logins", "Logins", "Logins",
                  "Sanctions", "Sanctions", "Sanctions", "Sanctions"],
        "Aging Bucket": ["0-7 Days", "8-14 Days", "15-21 Days", "21+ Days"] * 3,
        "Active Leads": [4200, 1800, 650, 210, 
                         2800, 1250, 480, 180, 
                         1100, 520, 140, 45]
    })
    
    return df_funnel, df_aging

df_vol, df_conv, df_multi, df_tat = get_lytd_data()
df_funnel, df_aging = get_current_funnel_data()

# ==========================================
# 3. APP HEADER & TAB DEFINITION
# ==========================================
st.title("🎯 Yocket BOFU Operations Pulse")
st.caption("Executive Dashboard | Live Trajectory & Funnel Tracking")
st.divider()

tab1, tab2, tab3 = st.tabs([
    "📊 1. LYTD Performance & Current Pipeline", 
    "📈 2. Operations & Bottlenecks (Pending)", 
    "🤝 3. Partner & Segmentation (Pending)"
])

# ==========================================
# 4. TAB 1: LYTD PERFORMANCE & CURRENT PIPELINE
# ==========================================
with tab1:
    
    # --- SECTION 1: EXECUTIVE SNAPSHOT ---
    st.subheader("1. Executive Snapshot (Current vs LYTD)")
    col1, col2, col3, col4 = st.columns(4)

    target_bp, target_logins, target_sanctions, target_pfs = 30000, 16000, 10000, 6000
    curr_bp = 21500
    curr_logins = 14200
    curr_sanctions = 7668
    curr_pfs = 4600

    with col1:
        st.markdown('<div class="macro-metric">', unsafe_allow_html=True)
        st.metric(label="BP / Shared", value=f"{curr_bp:,}", delta="+7.5% vs LYTD", delta_color="normal")
        st.progress(min(curr_bp / target_bp, 1.0))
        st.caption(f"🎯 **{(curr_bp/target_bp)*100:.1f}%** of Target ({target_bp:,})")

    with col2:
        st.metric(label="Logins", value=f"{curr_logins:,}", delta="+5.2% vs LYTD", delta_color="normal")
        st.progress(min(curr_logins / target_logins, 1.0))
        st.caption(f"🎯 **{(curr_logins/target_logins)*100:.1f}%** of Target ({target_logins:,})")

    with col3:
        st.metric(label="Sanctions", value=f"{curr_sanctions:,}", delta="+4.8% vs LYTD", delta_color="normal")
        st.progress(min(curr_sanctions / target_sanctions, 1.0))
        st.caption(f"🎯 **{(curr_sanctions/target_sanctions)*100:.1f}%** of Target ({target_sanctions:,})")

    with col4:
        st.metric(label="PFs", value=f"{curr_pfs:,}", delta="+7.9% vs LYTD", delta_color="normal")
        st.progress(min(curr_pfs / target_pfs, 1.0))
        st.caption(f"🎯 **{(curr_pfs/target_pfs)*100:.1f}%** of Target ({target_pfs:,})")

    st.divider()

    # --- SECTION 2: MoM VOLUME VARIANCE ---
    st.subheader("2. Month-on-Month Volume Variance")
    vol_metric = st.selectbox("Select Metric to View Variance:", ["BP", "Logins", "Sanctions", "PFs"], index=1)
    
    fig_vol = px.bar(
        df_vol, x="Month", y=vol_metric, color="Year", barmode="group",
        color_discrete_sequence=["#aec7e8", "#1f77b4"],
        title=f"{vol_metric} Volume: LYTD vs Current Year"
    )
    fig_vol.update_layout(template=plotly_theme, margin=dict(t=40, b=0, l=0, r=0), height=350, legend=dict(orientation="h", y=-0.2, title=None))
    st.plotly_chart(fig_vol, use_container_width=True)

    st.divider()

    # --- SECTION 3: MoM CONVERSION VARIANCE ---
    st.subheader("3. Month-on-Month Conversion Variance")
    conv_metric = st.selectbox("Select Conversion Stage:", ["BP to Login (%)", "Login to Sanction (%)", "Sanction to PF (%)"], index=1)
    
    fig_conv = px.line(
        df_conv, x="Month", y=conv_metric, color="Year", markers=True,
        color_discrete_sequence=["#aec7e8", "#ff9800"],
        title=f"{conv_metric} Trends: LYTD vs Current Year"
    )
    fig_conv.update_traces(line=dict(width=3), marker=dict(size=8))
    fig_conv.update_layout(template=plotly_theme, margin=dict(t=40, b=0, l=0, r=0), height=350, yaxis=dict(gridcolor=grid_color), legend=dict(orientation="h", y=-0.2, title=None))
    st.plotly_chart(fig_conv, use_container_width=True)

    st.divider()

    # --- SECTION 4 & 5: MULTI-RATES & TAT ---
    col_bottom_left, col_bottom_right = st.columns([1.2, 1])

    with col_bottom_left:
        st.subheader("4. Multi-Rate Comparison")
        st.caption("How many bank portals students are interacting with (Current vs LYTD).")
        
        df_multi_melted = df_multi.melt(id_vars=["Stage", "Target"], value_vars=["LYTD_Ratio", "Current_Ratio"], var_name="Year", value_name="Ratio")
        df_multi_melted["Year"] = df_multi_melted["Year"].replace({"LYTD_Ratio": "LYTD", "Current_Ratio": "Current"})
        
        fig_multi = px.bar(
            df_multi_melted, x="Stage", y="Ratio", color="Year", barmode="group",
            color_discrete_sequence=["#aec7e8", "#2ca02c"], text_auto='.2f'
        )
        
        for i, row in df_multi.iterrows():
            fig_multi.add_shape(
                type="line", x0=i-0.4, x1=i+0.4, y0=row["Target"], y1=row["Target"],
                line=dict(color="red", width=2, dash="dash")
            )
            
        fig_multi.update_layout(
            template=plotly_theme, height=300, margin=dict(t=20, b=0, l=0, r=0), 
            legend=dict(orientation="h", y=-0.2, title=None), yaxis_title="Multi-Ratio"
        )
        fig_multi.add_annotation(x=1, y=1.1, xref="paper", yref="paper", text="-- Red Line = Target", showarrow=False, font=dict(color="red", size=12))
        st.plotly_chart(fig_multi, use_container_width=True)

    with col_bottom_right:
        st.subheader("5. TAT Variance (Turnaround Time)")
        st.caption("Average days spent between stages (Lower is better).")
        st.write("##")
        
        for _, row in df_tat.iterrows():
            delta_val = row["Current_Days"] - row["LYTD_Days"]
            st.metric(
                label=f"⏳ {row['Conversion Stage']}", 
                value=f"{row['Current_Days']} Days", 
                delta=f"{delta_val:+.1f} Days vs LYTD ({row['LYTD_Days']})",
                delta_color="inverse" 
            )

    st.divider()

    # ==========================================
    # NEW EXTENSION: CURRENT YEAR FUNNEL & AGING
    # ==========================================
    st.write("## Current Year Funnel Intelligence")
    
    col_funnel, col_aging = st.columns([1, 1.2])
    
    with col_funnel:
        st.subheader("6. Conversion Cohort Funnel")
        st.caption("Total volume passing through active stages.")
        
        fig_funnel = go.Figure(go.Funnel(
            y=df_funnel["Stage"],
            x=df_funnel["Count"],
            textinfo="value+percent initial",
            marker={"color": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]}
        ))
        fig_funnel.update_layout(template=plotly_theme, height=350, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_funnel, use_container_width=True)
        
    with col_aging:
        st.subheader("7. Active Pipeline Aging (Stuck Leads)")
        st.caption("Current leads sitting in stages, broken down by age.")
        
        # Ordered categories for logic flow
        aging_order = ["0-7 Days", "8-14 Days", "15-21 Days", "21+ Days"]
        color_map = {
            "0-7 Days": "#2ca02c",    # Green
            "8-14 Days": "#ffc107",   # Yellow
            "15-21 Days": "#ff7f0e",  # Orange
            "21+ Days": "#d62728"     # Red
        }
        
        fig_aging = px.bar(
            df_aging, y="Stage", x="Active Leads", color="Aging Bucket",
            orientation='h',
            color_discrete_map=color_map,
            category_orders={"Aging Bucket": aging_order}
        )
        fig_aging.update_layout(
            template=plotly_theme, 
            height=350, 
            barmode="stack",
            margin=dict(t=20, b=0, l=0, r=0),
            legend=dict(orientation="h", y=-0.2, title=None)
        )
        st.plotly_chart(fig_aging, use_container_width=True)

# ------------------------------------------
# TAB 2 & 3 PLACEHOLDERS
# ------------------------------------------
with tab2:
    st.info("Tab 2 will be built in the next iteration.")
with tab3:
    st.info("Tab 3 will be built in the next iteration.")
