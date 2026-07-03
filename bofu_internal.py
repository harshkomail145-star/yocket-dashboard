import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# 1. PAGE SETUP & CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Yocket BOFU Command Center",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Styling for metrics and progress bars
st.markdown("""
    <style>
    .stMetric {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #1f77b4;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MOCK DATA GENERATION (BOFU Metrics)
# ==========================================
@st.cache_data
def get_bofu_data():
    # 5-Week Trend Data
    df_trend = pd.DataFrame({
        "Week": ["W4 (-4 weeks)", "W3 (-3 weeks)", "W2 (-2 weeks)", "W1 (last week)", "W0 (ongoing week)"],
        "Logins": [190, 150, 175, 149, 75],
        "Sanctions": [80, 68, 97, 102, 43],
        "PFs": [61, 60, 63, 63, 53]
    })
    
    # Segment Conversion Data (Finco, Non-Finco, LS, GeeBee)
    df_segments = pd.DataFrame({
        "Segment": ["Overall", "Finco", "Non Finco", "LS", "GeeBee"],
        "LQ_to_Login_Pct": [20, 40, 16, 20, 56],
        "Login_to_Sanction_Pct": [51, 73, 44, 51, 46],
        "Sanction_to_PF_Pct": [67, 64, 64, 71, 67]
    })
    
    # Core Conversion Target Tracking
    df_targets = pd.DataFrame({
        "Stage": ["BP to Login", "Login to Sanction", "Sanction to PF", "Login to PF"],
        "Current_Achieved": [94, 54, 60, 32],
        "YTD_Target": [99, 59, 65, 38]
    })
    
    return df_trend, df_segments, df_targets

df_trend, df_segments, df_targets = get_bofu_data()

# ==========================================
# 3. APP HEADER
# ==========================================
st.title("🎯 Yocket Funnel Operations Pulse")
st.caption("Weekly Business Review | Live BOFU Tracking for Fall Season")
st.divider()

# ==========================================
# 4. DASHBOARD LAYOUT
# ==========================================

# --- SECTION 1: WEEKLY VELOCITY ---
st.subheader("1. Weekly Velocity Pulse (W1 vs Prev Week)")
st.write("Tracking immediate volume movements at the bottom of the funnel.")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Logins (Last Week)", value="149", delta="-26 vs prev week", delta_color="inverse")
with col2:
    st.metric(label="Sanctions (Last Week)", value="102", delta="5 vs prev week", delta_color="normal")
with col3:
    st.metric(label="PFs (Last Week)", value="63", delta="0 vs prev week", delta_color="off")
    
st.write("##")

# --- SECTION 2: TIMELINE SNAPSHOT ---
st.subheader("2. Timeline Snapshot (WOW Trend)")
st.info("💡 **Operational Note:** Given the lag between login and downstream conversion, increased logins in W2 are translating into Sanction/PF holds in W1.")

fig_trend = go.Figure()
fig_trend.add_trace(go.Scatter(x=df_trend["Week"], y=df_trend["Logins"], mode='lines+markers', name='Logins', line=dict(color='#1f77b4', width=3)))
fig_trend.add_trace(go.Scatter(x=df_trend["Week"], y=df_trend["Sanctions"], mode='lines+markers', name='Sanctions', line=dict(color='#2ca02c', width=3, dash='dash')))
fig_trend.add_trace(go.Scatter(x=df_trend["Week"], y=df_trend["PFs"], mode='lines+markers', name='PFs', line=dict(color='#d62728', width=3)))

fig_trend.update_layout(
    title="5-Week Velocity Trajectory", 
    template="plotly_white", 
    yaxis_title="Volume Count", 
    legend=dict(orientation="h", y=-0.15),
    height=400
)
st.plotly_chart(fig_trend, use_container_width=True)

st.divider()

# --- SECTION 3: RATIOS & TARGETS ---
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("3. Multi-Sharing Ratios")
    st.caption("Tracking how many banks/portals a single student is interacting with.")
    
    st.write("##")
    # BP / Sharing Multi
    st.write("**BP / Sharing Multi** (Target: 4.0)")
    st.progress(min(4.2 / 5.0, 1.0)) 
    st.caption("Current: **4.2** 🟢 Exceeding target (Watch WOW decline to 3.6)")
    
    st.write("---")
    
    # Login Multi
    st.write("**Login Multi** (Target: 2.2)")
    st.progress(min(1.9 / 3.0, 1.0)) 
    st.caption("Current: **1.9** 🔴 Needs Improvement")
    
    st.write("---")
    
    # Sanction Multi
    st.write("**Sanction Multi** (Target: 1.7)")
    st.progress(min(1.45 / 3.0, 1.0)) 
    st.caption("Current: **1.45** 🔴 Needs Improvement")

with col_right:
    st.subheader("4. Stage Conversion vs Target")
    st.caption("Tracking actual BOFU conversion rates against YTD targets.")
    
    fig_targets = go.Figure()
    fig_targets.add_trace(go.Bar(
        y=df_targets["Stage"], x=df_targets["Current_Achieved"], 
        name="Current Achieved (%)", orientation='h', marker_color='#1f77b4'
    ))
    fig_targets.add_trace(go.Bar(
        y=df_targets["Stage"], x=df_targets["YTD_Target"], 
        name="YTD Target (%)", orientation='h', marker_color='#aec7e8'
    ))
    
    fig_targets.update_layout(
        barmode='group', 
        template='plotly_white',
        xaxis_title="Conversion Percentage (%)",
        height=350,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", y=-0.2)
    )
    st.plotly_chart(fig_targets, use_container_width=True)

st.divider()

# --- SECTION 4: SEGMENT PERFORMANCE ---
st.subheader("5. BOFU Conversion Snapshot by Segment")
st.caption("Side-by-side comparison of Finco, Non-Finco, LS, and GeeBee pipelines.")

fig_segments = go.Figure()
fig_segments.add_trace(go.Bar(x=df_segments["Segment"], y=df_segments["LQ_to_Login_Pct"], name="LQ to Login (%)", marker_color='#ff9800'))
fig_segments.add_trace(go.Bar(x=df_segments["Segment"], y=df_segments["Login_to_Sanction_Pct"], name="Login to Sanction (%)", marker_color='#2ca02c'))
fig_segments.add_trace(go.Bar(x=df_segments["Segment"], y=df_segments["Sanction_to_PF_Pct"], name="Sanction to PF (%)", marker_color='#9467bd'))

fig_segments.update_layout(
    barmode='group',
    template='plotly_white',
    yaxis_title="Conversion Rate (%)",
    legend=dict(orientation="h", y=1.1),
    height=450
)
st.plotly_chart(fig_segments, use_container_width=True)
