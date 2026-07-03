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
    initial_sidebar_state="expanded" # Expanded to show the new toggle
)

# --- THEME TOGGLE (SIDEBAR) ---
st.sidebar.title("⚙️ Dashboard Controls")
dark_mode = st.sidebar.toggle("🌙 Enable Dark Mode", value=False)

# --- DYNAMIC THEMING VARIABLES ---
if dark_mode:
    # Neon/Dark Theme Settings
    plotly_theme = "plotly_dark"
    gauge_bg = "#333333"      # Dark charcoal for empty gauge space
    target_line = "white"     # White lines for bullet chart targets
    subtitle_color = "#aaaaaa"# Lighter gray for HTML text in dark mode
    metric_bg = "#262730"     # Streamlit's native dark widget background
    metric_text = "#ffffff"
else:
    # Light/Clean Theme Settings
    plotly_theme = "plotly_white"
    gauge_bg = "#f4f4f4"      # Light gray for empty gauge space
    target_line = "black"     # Black lines for bullet chart targets
    subtitle_color = "gray"   # Standard gray for HTML text
    metric_bg = "#f8f9fa"     # Light gray background
    metric_text = "#31333F"

# Injecting Dynamic CSS for the Metric Cards
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
# 2. MOCK DATA GENERATION 
# ==========================================
@st.cache_data
def get_bofu_data():
    df_trend = pd.DataFrame({
        "Week": ["W4 (-4 weeks)", "W3 (-3 weeks)", "W2 (-2 weeks)", "W1 (last week)", "W0 (ongoing week)"],
        "Logins": [190, 150, 175, 149, 75],
        "Sanctions": [80, 68, 97, 102, 43],
        "PFs": [61, 60, 63, 63, 53]
    })
    
    df_segments = pd.DataFrame({
        "Segment": ["Overall", "Finco", "Non Finco", "LS", "GeeBee"],
        "LQ to Login (%)": [20, 40, 16, 20, 56],
        "Login to Sanction (%)": [51, 73, 44, 51, 46],
        "Sanction to PF (%)": [67, 64, 64, 71, 67]
    })
    
    df_targets = pd.DataFrame({
        "Stage": ["BP to Login", "Login to Sanction", "Sanction to PF", "Login to PF"],
        "Current_Achieved": [94, 54, 60, 32],
        "YTD_Target": [99, 59, 65, 38]
    })
    
    weeks = [f"Week {i}" for i in range(1, 13)]
    fall_25_cumulative = [50, 120, 210, 310, 450, 600, 780, 920, 1100, 1250, 1400, 1586]
    fall_26_cumulative = [65, 145, 260, 390, 550, 730, 900, 1150, 1320, 1500, None, None]
    
    df_season_traj = pd.DataFrame({
        "Week": weeks,
        "Fall 2025 (Last Season)": fall_25_cumulative,
        "Fall 2026 (This Season YTD)": fall_26_cumulative
    })

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

# Create 4 balanced columns to include BP
col1, col2, col3, col4 = st.columns(4)

# Mock Targets for the Progress Bars
target_bp = 25000
target_logins = 16000
target_sanctions = 10000
target_pfs = 6000

# Actual values from your data
current_bp = 21500
current_logins = 14200
current_sanctions = 7668
current_pfs = 4600

with col1:
    st.metric(label="BP / Shared (vs Last Year)", value=f"{current_bp:,}", delta="+15% vs LYTD", delta_color="normal")
    st.progress(min(current_bp / target_bp, 1.0))
    st.caption(f"🎯 **{(current_bp/target_bp)*100:.1f}%** of Target ({target_bp:,})")

with col2:
    st.metric(label="Logins (vs Last Year)", value=f"{current_logins:,}", delta="+12% vs LYTD", delta_color="normal")
    st.progress(min(current_logins / target_logins, 1.0))
    st.caption(f"🎯 **{(current_logins/target_logins)*100:.1f}%** of Target ({target_logins:,})")

with col3:
    st.metric(label="Sanctions (vs Last Year)", value=f"{current_sanctions:,}", delta="-1% vs LYTD", delta_color="inverse")
    st.progress(min(current_sanctions / target_sanctions, 1.0))
    st.caption(f"🎯 **{(current_sanctions/target_sanctions)*100:.1f}%** of Target ({target_sanctions:,})")

with col4:
    st.metric(label="PFs (vs Last Year)", value=f"{current_pfs:,}", delta="+8% vs LYTD", delta_color="normal")
    st.progress(min(current_pfs / target_pfs, 1.0))
    st.caption(f"🎯 **{(current_pfs/target_pfs)*100:.1f}%** of Target ({target_pfs:,})")

st.write("##")

st.write("**Cumulative Pipeline Growth: Fall '25 vs. Fall '26 (Current Season)**")
fig_season = go.Figure()
fig_season.add_trace(go.Scatter(x=df_season_traj["Week"], y=df_season_traj["Fall 2025 (Last Season)"], fill='tozeroy', mode='lines', name='Fall 2025 (Final)', line=dict(color='#aec7e8', dash='dot')))
fig_season.add_trace(go.Scatter(x=df_season_traj["Week"], y=df_season_traj["Fall 2026 (This Season YTD)"], fill='tozeroy', mode='lines+markers', name='Fall 2026 (Current)', line=dict(color='#1f77b4', width=3)))
fig_season.update_layout(template=plotly_theme, yaxis_title="Cumulative Volume", height=300, margin=dict(l=0, r=0, t=30, b=0), legend=dict(x=0.02, y=0.9))
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
    fig_trend.update_layout(template=plotly_theme, yaxis_title="Volume Count", height=320, margin=dict(l=0, r=0, t=30, b=0), legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig_trend, use_container_width=True)

st.divider()

# ==========================================
# 6. SECTION 3: BOTTLENECKS & OPERATIONS
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
    fig_drop = px.bar(df_dropoffs, y="Reason", x="Count", orientation='h', template=plotly_theme, color_discrete_sequence=['#ff7f0e'])
    fig_drop.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0), yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_drop, use_container_width=True)

st.divider()

# ==========================================
# 7. SECTION 4: ADVANCED CONVERSION DIAGNOSTICS
# ==========================================
st.subheader("6. Advanced Conversion Diagnostics")
st.caption("High-fidelity breakdown of Multi-ratios, target pacing, and segment performance.")

# --- Row 1: The Multi-Sharing Gauges ---
fig_gauges = go.Figure()

# Gauge 1: BP/Sharing 
fig_gauges.add_trace(go.Indicator(
    mode="gauge+number+delta", value=4.2, delta={'reference': 4.0, 'position': "top"},
    title={'text': f"BP/Sharing Multi<br><span style='font-size:12px;color:{subtitle_color}'>Target: 4.0</span>"},
    gauge={'axis': {'range': [None, 6]}, 'bar': {'color': "#2ca02c"}, 'steps': [{'range': [0, 4.0], 'color': gauge_bg}]},
    domain={'row': 0, 'column': 0}
))

# Gauge 2: Login Multi 
fig_gauges.add_trace(go.Indicator(
    mode="gauge+number+delta", value=1.9, delta={'reference': 2.2, 'position': "top"},
    title={'text': f"Login Multi<br><span style='font-size:12px;color:{subtitle_color}'>Target: 2.2</span>"},
    gauge={'axis': {'range': [None, 4]}, 'bar': {'color': "#d62728"}, 'steps': [{'range': [0, 2.2], 'color': gauge_bg}]},
    domain={'row': 0, 'column': 1}
))

# Gauge 3: Sanction Multi 
fig_gauges.add_trace(go.Indicator(
    mode="gauge+number+delta", value=1.45, delta={'reference': 1.7, 'position': "top"},
    title={'text': f"Sanction Multi<br><span style='font-size:12px;color:{subtitle_color}'>Target: 1.7</span>"},
    gauge={'axis': {'range': [None, 3]}, 'bar': {'color': "#d62728"}, 'steps': [{'range': [0, 1.7], 'color': gauge_bg}]},
    domain={'row': 0, 'column': 2}
))

fig_gauges.update_layout(
    grid={'rows': 1, 'columns': 3, 'pattern': "independent"}, 
    height=300, 
    margin=dict(t=100, b=20, l=20, r=20),
    template=plotly_theme
)
st.plotly_chart(fig_gauges, use_container_width=True)

st.write("##")

# --- Row 2: Bullet Charts & Segment Heatmap ---
col_diag_left, col_diag_right = st.columns([1, 1.5])

with col_diag_left:
    st.write("**Stage Conversion vs YTD Targets**")
    fig_bullets = go.Figure()
    
    # Create a high-tech Bullet chart for each stage, dynamically coloring the target line
    for i, row in df_targets.iterrows():
        color = "#1f77b4" if row["Current_Achieved"] >= row["YTD_Target"] else "#ff7f0e"
        fig_bullets.add_trace(go.Indicator(
            mode="number+gauge", value=row["Current_Achieved"], number={'suffix': "%", 'font': {'size': 20}},
            title={'text': row["Stage"], 'font': {'size': 13}},
            gauge={
                'shape': "bullet", 'axis': {'range': [None, 100], 'visible': False},
                'threshold': {'line': {'color': target_line, 'width': 3}, 'thickness': 0.75, 'value': row["YTD_Target"]},
                'bar': {'color': color},
                'steps': [{'range': [0, 100], 'color': gauge_bg}]
            },
            domain={'row': i, 'column': 0}
        ))
        
    fig_bullets.update_layout(
        grid={'rows': 4, 'columns': 1, 'pattern': "independent"}, 
        height=350, 
        margin=dict(t=20, b=20, l=120, r=20),
        template=plotly_theme
    )
    st.plotly_chart(fig_bullets, use_container_width=True)

with col_diag_right:
    st.write("**Segment Snapshot (Actuals %)**")
    
    df_melted = df_segments.melt(id_vars="Segment", var_name="Stage", value_name="Percentage")
    
    fig_bars = px.bar(
        df_melted, x="Segment", y="Percentage", color="Stage", 
        barmode="group", text_auto='%', 
        color_discrete_sequence=["#ff9800", "#2ca02c", "#9467bd"]
    )
    
    fig_bars.update_layout(
        template=plotly_theme, 
        height=350, 
        yaxis=dict(visible=False),
        plot_bgcolor="rgba(0,0,0,0)", 
        margin=dict(t=20, b=20, l=0, r=0),
        legend=dict(orientation="h", y=-0.15, title=None)
    )
    
    # Force text color to adapt to the dark/light background so it never disappears
    text_color = "white" if dark_mode else "black"
    fig_bars.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False, textfont=dict(color=text_color))
    
    st.plotly_chart(fig_bars, use_container_width=True)
