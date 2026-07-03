import streamlit as st
import pandas as pd
import plotly.express as px
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
    .macro-metric {
        border-left: 5px solid #ff9800 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MOCK DATA GENERATION 
# ==========================================
@st.cache_data
def get_bofu_data():
    # --- Existing WBR Data ---
    df_trend = pd.DataFrame({
        "Week": ["W4 (-4 weeks)", "W3 (-3 weeks)", "W2 (-2 weeks)", "W1 (last week)", "W0 (ongoing week)"],
        "Logins": [190, 150, 175, 149, 75],
        "Sanctions": [80, 68, 97, 102, 43],
        "PFs": [61, 60, 63, 63, 53]
    })
    
    df_segments = pd.DataFrame({
        "Segment": ["Overall", "Finco", "Non Finco", "LS", "GeeBee"],
        "LQ_to_Login_Pct": [20, 40, 16, 20, 56],
        "Login_to_Sanction_Pct": [51, 73, 44, 51, 46],
        "Sanction_to_PF_Pct": [67, 64, 64, 71, 67]
    })
    
    df_targets = pd.DataFrame({
        "Stage": ["BP to Login", "Login to Sanction", "Sanction to PF", "Login to PF"],
        "Current_Achieved": [94, 54, 60, 32],
        "YTD_Target": [99, 59, 65, 38]
    })
    
    # --- NEW: Macro Achievement Data ---
    # Cumulative trajectory for Fall 25 vs Fall 26 (Week 1 to Week 12)
    weeks = [f"Week {i}" for i in range(1, 13)]
    fall_25_cumulative = [50, 120, 210, 310, 450, 600, 780, 920, 1100, 1250, 1400, 1586]
    fall_26_cumulative = [65, 145, 260, 390, 550, 730, 900, 1150, 1320, 1500, None, None] # Ahead of last year, currently at week 10
    
    df_season_traj = pd.DataFrame({
        "Week": weeks,
        "Fall 2025 (Last Season)": fall_25_cumulative,
        "Fall 2026 (This Season YTD)": fall_26_cumulative
    })

    # --- NEW: Suggested Operational Data ---
    df_dropoffs = pd.DataFrame({
        "Reason": ["Better Interest Rate Elsewhere", "Visa Rejection", "University Changed", "Co-applicant Credit Score", "Lender Processing Delay"],
        "Count": [145, 82, 54, 39, 27]
    })
    
    return df_trend, df_segments, df_targets, df_season_traj, df_dropoffs

df_trend, df_segments, df_targets, df_season_traj, df_dropoffs = get_bofu_data()

# ==========================================
# 3. APP HEADER
# ==========================================
st.title("🎯 Yocket BOFU Operations Pulse")
st.caption("Executive Dashboard | Live Trajectory & Funnel Tracking")
st.divider()

# ==========================================
# 4. SECTION 1: MACRO ACHIEVEMENTS
# ==========================================
st.subheader("1. Executive Snapshot: Overall Achievements")

# Macro KPIs
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown('<div class="macro-metric">', unsafe_allow_html=True)
    st.metric(label="Overall Achieved vs Target (PFs)", value="8,450", delta="Target: 10,000 (84.5%)", delta_color="normal")
    st.progress(0.845)
with col2:
    st.metric(label="Logins (This Year vs Last Year)", value="14,200", delta="+12% vs LYTD", delta_color="normal")
with col3:
    st.metric(label="Sanctions (This Year vs Last Year)", value="7,668", delta="-1% vs LYTD", delta_color="inverse")
with col4:
    st.metric(label="PFs (This Year vs Last Year)", value="4,600", delta="+8% vs LYTD", delta_color="normal")

st.write("##")

# Season vs Season Trajectory Chart
st.write("**Cumulative Pipeline Growth: Fall '25 vs. Fall '26 (Current Season)**")
fig_season = go.Figure()
fig_season.add_trace(go.Scatter(x=df_season_traj["Week"], y=df_season_traj["Fall 2025 (Last Season)"], fill='tozeroy', mode='lines', name='Fall 2025 (Final)', line=dict(color='#aec7e8', dash='dot')))
fig_season.add_trace(go.Scatter(x=df_season_traj["Week"], y=df_season_traj["Fall 2026 (This Season YTD)"], fill='tozeroy', mode='lines+markers', name='Fall 2026 (Current)', line=dict(color='#1f77b4', width=3)))

fig_season.update_layout(
    template="plotly_white", 
    yaxis_title="Cumulative Logins", 
    height=300,
    margin=dict(l=0, r=0, t=30, b=0),
    legend=dict(x=0.02, y=0.9)
)
st.plotly_chart(fig_season, use_container_width=True)

st.divider()

# ==========================================
# 5. SECTION 2: WEEKLY VELOCITY & TRENDS
# ==========================================
col_trend_left, col_trend_right = st.columns([1, 2])

with col_trend_left:
    st.subheader("2. Weekly Velocity (W1 vs Prev Week)")
    st.metric(label="Logins (Last Week)", value="149", delta="-26 vs prev week", delta_color="inverse")
    st.metric(label="Sanctions (Last Week)", value="102", delta="5 vs prev week", delta_color="normal")
    st.metric(label="PFs (Last Week)", value="63", delta="0 vs prev week", delta_color="off")
    
with col_trend_right:
    st.subheader("3. 5-Week Trailing Momentum")
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(x=df_trend["Week"], y=df_trend["Logins"], mode='lines+markers', name='Logins', line=dict(color='#1f77b4', width=3)))
    fig_trend.add_trace(go.Scatter(x=df_trend["Week"], y=df_trend["Sanctions"], mode='lines+markers', name='Sanctions', line=dict(color='#2ca02c', width=3, dash='dash')))
    fig_trend.add_trace(go.Scatter(x=df_trend["Week"], y=df_trend["PFs"], mode='lines+markers', name='PFs', line=dict(color='#d62728', width=3)))

    fig_trend.update_layout(
        template="plotly_white", 
        yaxis_title="Volume Count", 
        height=320,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", y=-0.15)
    )
    st.plotly_chart(fig_trend, use_container_width=True)

st.divider()

# ==========================================
# 6. SECTION 3: BOTTLENECKS & OPERATIONS (SUGGESTIONS)
# ==========================================
col_ops_left, col_ops_right = st.columns(2)

with col_ops_left:
    st.subheader("4. Operational Turnaround Time (TAT)")
    st.caption("Average processing speed. Target: < 7 Days overall.")
    
    tat_col1, tat_col2 = st.columns(2)
    with tat_col1:
        st.metric(label="Avg TAT: Login ➔ Sanction", value="4.2 Days", delta="+0.5 Days vs Last Week", delta_color="inverse")
    with tat_col2:
        st.metric(label="Avg TAT: Sanction ➔ PF", value="2.8 Days", delta="-0.2 Days vs Last Week", delta_color="normal")

with col_ops_right:
    st.subheader("5. Sanction Drop-off Diagnostics")
    st.caption("Top reasons why approved Sanctions failed to convert to PFs.")
    fig_drop = px.bar(df_dropoffs, y="Reason", x="Count", orientation='h', template="plotly_white", color_discrete_sequence=['#ff7f0e'])
    fig_drop.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0), yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_drop, use_container_width=True)

st.divider()

# ==========================================
# 7. SECTION 4: RATIOS, TARGETS & SEGMENTS
# ==========================================
st.subheader("6. Conversion Efficiency & Segments")

col_bot_1, col_bot_2, col_bot_3 = st.columns([1, 1.5, 1.5])

with col_bot_1:
    st.write("**Multi-Sharing Indicators**")
    st.write("**BP / Sharing Multi:** 4.2 🟢 (Tgt: 4.0)")
    st.write("**Login Multi:** 1.9 🔴 (Tgt: 2.2)")
    st.write("**Sanction Multi:** 1.45 🔴 (Tgt: 1.7)")

with col_bot_2:
    st.write("**Stage Conversion vs YTD Targets**")
    fig_targets = go.Figure()
    fig_targets.add_trace(go.Bar(y=df_targets["Stage"], x=df_targets["Current_Achieved"], name="Actual %", orientation='h', marker_color='#1f77b4'))
    fig_targets.add_trace(go.Bar(y=df_targets["Stage"], x=df_targets["YTD_Target"], name="Target %", orientation='h', marker_color='#aec7e8'))
    fig_targets.update_layout(barmode='group', template='plotly_white', height=250, margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig_targets, use_container_width=True)

with col_bot_3:
    st.write("**Segment Snapshot (Actuals %)**")
    fig_segments = go.Figure()
    fig_segments.add_trace(go.Bar(x=df_segments["Segment"], y=df_segments["LQ_to_Login_Pct"], name="LQ to Login", marker_color='#ff9800'))
    fig_segments.add_trace(go.Bar(x=df_segments["Segment"], y=df_segments["Login_to_Sanction_Pct"], name="Login to Sanction", marker_color='#2ca02c'))
    fig_segments.add_trace(go.Bar(x=df_segments["Segment"], y=df_segments["Sanction_to_PF_Pct"], name="Sanction to PF", marker_color='#9467bd'))
    fig_segments.update_layout(barmode='group', template='plotly_white', height=250, margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig_segments, use_container_width=True)
