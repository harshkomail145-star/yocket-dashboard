import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="Fall 26 Analytics", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; border-top: 4px solid #4f46e5; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1); }
    /* Stylized section headers for the single-page layout */
    .section-header { background-color: #ffffff; padding: 15px; border-radius: 8px; border-left: 5px solid #4f46e5; margin-top: 30px; margin-bottom: 15px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);}
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Fall 26 Command Center")

# --- 2. SIDEBAR FILTERS ---
with st.sidebar:
    st.header("⚙️ Global Filters")
    selected_banks = st.multiselect(
        "Select Bank Partners", 
        ["Auxilo", "Credila", "Avanse", "SBI", "ICICI"], 
        default=["Credila"]
    )
    st.divider()
    st.caption("UI Mode: MOCK DATA 🟢")

# --- 3. DOWNLOAD REPORT FEATURE ---
# This generates a Markdown string containing all the current numbers
def generate_markdown_report():
    report = """# Fall 26 Command Center - Analytics Report
*Generated on: {}*

## 1. Y-o-Y Metric Comparison (Fall 26 vs Fall 25)
* **Shared:** 2,855 (Up 38.1% from 2,067)
* **Login:** 2,225 (Up 27.0% from 1,752)
* **Sanction:** 1,110 (Up 22.2% from 908)
* **PF:** 588 (Up 25.9% from 467)

## 2. Shared Lead Funnel Progression
* **Master Cohort:** 2,783
* **Login Stage:** 195 Current | 430 Lost (77% Conv)
* **Sanction Stage:** 453 Current | 643 Lost (48% Conv)
* **PF Stage:** 448 Current | 57 Lost (49% Conv)

## 3. Active Workable Leads
* **BP Stage:** 80 Workable (34 under 7 days, 46 over 7 days)
* **Login Stage:** 55 Workable (30 under 7 days, 25 over 7 days)
* **Sanction Stage:** 40 Workable (27 under 7 days, 13 over 7 days)

## 4. Lost Analysis Highlights
* Highest lost volume from BP stage (Not Doable: 225, Not Interested: 222).
* Total of 55 files lost to competitors (paid PF elsewhere).
"""
    return report.format(datetime.now().strftime("%Y-%m-%d %H:%M"))

# The Download Button
st.download_button(
    label="📥 Download Report for Google Docs (.md)",
    data=generate_markdown_report(),
    file_name=f"Fall_26_Report_{datetime.now().strftime('%Y%m%d')}.md",
    mime="text/markdown",
    help="Download this file and open it with Google Docs for a formatted text report."
)

st.divider()

# ==========================================
# SECTION 1: Y-O-Y METRICS
# ==========================================
st.markdown('<div class="section-header"><h2>📈 1. Y-o-Y Metrics (Fall 26 vs Fall 25)</h2></div>', unsafe_allow_html=True)

# 1. Top Level Metrics Chart
stages = ['Shared', 'Login', 'Sanction', 'PF']
fall_25_data = [2067, 1752, 908, 467]
fall_26_data = [2855, 2225, 1110, 588]
yoy_growth = ['+38.1%', '+27.0%', '+22.2%', '+25.9%']

fig_top_metrics = go.Figure()

fig_top_metrics.add_trace(go.Bar(
    name='Fall 25 Till Date', x=stages, y=fall_25_data, marker_color='#6a96b9', text=fall_25_data, textposition='outside', textfont=dict(size=14, color='black')
))

fig_top_metrics.add_trace(go.Bar(
    name='Fall 26 Till Date', x=stages, y=fall_26_data, marker_color='#1f4e71', text=fall_26_data, textposition='outside', textfont=dict(size=14, color='black')
))

growth_annotations = []
for i, stage in enumerate(stages):
    y_max = max(fall_25_data[i], fall_26_data[i])
    growth_annotations.append(dict(
        x=stage,
        y=y_max + 350, 
        text=f"<b>⬆ {yoy_growth[i]}</b><br><span style='font-size:11px'>YoY Growth</span>",
        showarrow=False,
        font=dict(size=14, color="black"),
        bgcolor="#f8fafc",
        bordercolor="#94a3b8", 
        borderwidth=1,
        borderpad=6
    ))

fig_top_metrics.update_layout(
    barmode='group', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(gridcolor='#e2e8f0', range=[0, 3600]),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    annotations=growth_annotations, margin=dict(t=80) 
)
st.plotly_chart(fig_top_metrics, use_container_width=True)


# ==========================================
# SECTION 2: FALL 26 M-o-M 
# ==========================================
st.markdown('<div class="section-header"><h2>📅 2. Fall 26 M-o-M Logins</h2></div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.subheader("YoY Monthly Logins")
    mock_yoy_monthly = pd.DataFrame({
        'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        'Fall 26': [219, 397, 444, 436, 377, 352],
        'Fall 25': [243, 297, 380, 322, 294, 231]
    })
    
    fig_yoy_bar = go.Figure(data=[
        go.Bar(name='Fall 26', x=mock_yoy_monthly['Month'], y=mock_yoy_monthly['Fall 26'], marker_color='#60a5fa', text=mock_yoy_monthly['Fall 26'], textposition='auto'),
        go.Bar(name='Fall 25', x=mock_yoy_monthly['Month'], y=mock_yoy_monthly['Fall 25'], marker_color='#ef4444', text=mock_yoy_monthly['Fall 25'], textposition='auto')
    ])
    fig_yoy_bar.update_layout(barmode='group', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(gridcolor='#e2e8f0'), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig_yoy_bar, use_container_width=True)

with col2:
    st.subheader("MoM Progression by Stage")
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    stages_mom = ['shared', 'login', 'sanction', 'pf']
    
    mock_mom = pd.DataFrame({
        'Month': np.repeat(months, 4),
        'Stage': stages_mom * 6,
        'Value': [
            265, 219, 85, 36,   # Jan
            575, 397, 185, 66,  # Feb
            576, 444, 219, 93,  # Mar
            535, 437, 255, 126, # Apr
            484, 377, 205, 146, # May
            447, 352, 162, 121  # Jun
        ]
    })
    
    color_map = {'shared': '#3b82f6', 'login': '#ef4444', 'sanction': '#fbbf24', 'pf': '#22c55e'}
    fig_mom = px.bar(mock_mom, x='Month', y='Value', color='Stage', barmode='group', text='Value', color_discrete_map=color_map)
    fig_mom.update_traces(textposition='outside')
    fig_mom.update_layout(plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(gridcolor='#e2e8f0'), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig_mom, use_container_width=True)


# ==========================================
# SECTION 3: SHARED LEAD COHORT
# ==========================================
st.markdown('<div class="section-header"><h2>🧬 3. Shared Leads Funnel</h2></div>', unsafe_allow_html=True)

stages_funnel = ['Shared', 'Login', 'Sanction', 'PF']
totals = [2783, 2148, 1021, 504]
custom_text = [
    "<b>Master Cohort</b>",
    "<b>Current:</b> 195 | <b>Lost:</b> 430",
    "<b>Current:</b> 453 | <b>Lost:</b> 643",
    "<b>Current:</b> 448 | <b>Lost:</b> 57"
]

fig_funnel = go.Figure(go.Funnel(
    y=stages_funnel, x=totals, text=custom_text, textposition="inside",
    textinfo="value+text+percent previous", 
    marker={"color": ["#4f46e5", "#6366f1", "#818cf8", "#a5b4fc"], "line": {"width": [2, 2, 2, 2], "color": ["white", "white", "white", "white"]}},
    connector={"line": {"color": "#e2e8f0", "dash": "dot", "width": 2}}
))

fig_funnel.update_layout(margin={"t": 40, "b": 40}, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', yaxis=dict(title_text="", showline=False, tickfont=dict(size=14, weight="bold")), xaxis=dict(showticklabels=False))
st.plotly_chart(fig_funnel, use_container_width=True)


# ==========================================
# SECTION 4: ACTIVE AGING
# ==========================================
st.markdown('<div class="section-header"><h2>⏱️ 4. Active Aging & Competitor Loss</h2></div>', unsafe_allow_html=True)

col_a1, col_a2, col_a3 = st.columns(3)

with col_a1:
    st.markdown("### BP Stage")
    st.metric("BP Active Leads", "100")
    st.metric("Paid PF to Competitor", "20", "-20", delta_color="inverse")
    st.info("**Active Workable: 80**\n\n🟢 Less than 7 Days: 34\n\n🔴 More than 7 Days: 46")
    
with col_a2:
    st.markdown("### Login Stage")
    st.metric("Login Active Leads", "70")
    st.metric("Paid PF to Competitor", "15", "-15", delta_color="inverse")
    st.info("**Active Workable: 55**\n\n🟢 Less than 7 Days: 30\n\n🔴 More than 7 Days: 25")
    
with col_a3:
    st.markdown("### Sanction Stage")
    st.metric("Sanction Active Leads", "60")
    st.metric("Paid PF to Competitor", "20", "-20", delta_color="inverse")
    st.info("**Active Workable: 40**\n\n🟢 Less than 7 Days: 27\n\n🔴 More than 7 Days: 13")


# ==========================================
# SECTION 5: LOST ANALYSIS
# ==========================================
st.markdown('<div class="section-header"><h2>🚨 5. Lost Analysis</h2></div>', unsafe_allow_html=True)

col_l1, col_l2 = st.columns(2)

with col_l1:
    st.subheader("Lost Potential (%) vs Total Files")
    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    
    stages_lost = ['Lost from BP', 'Lost from Login', 'Lost from Sanction']
    total_files = [200, 300, 100]
    went_ahead = [145, 204, 85]
    lost_potential = [72.5, 68.0, 85.0]
    
    fig_dual.add_trace(go.Bar(name='Total Files', x=stages_lost, y=total_files, marker_color='#60a5fa'), secondary_y=False)
    fig_dual.add_trace(go.Bar(name='Went Ahead in Other Banks', x=stages_lost, y=went_ahead, marker_color='#ef4444'), secondary_y=False)
    fig_dual.add_trace(go.Scatter(name='% Lost Potential', x=stages_lost, y=lost_potential, mode='lines+markers+text', marker=dict(size=12, color='#fbbf24'), line=dict(width=4, color='#fbbf24'), text=[f"{x}%" for x in lost_potential], textposition="top center", textfont=dict(weight='bold')), secondary_y=True)
    
    fig_dual.update_layout(barmode='group', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=-0.15, x=0.2))
    fig_dual.update_yaxes(title_text="Number of Files", secondary_y=False, gridcolor='#e2e8f0')
    fig_dual.update_yaxes(title_text="% Lost Potential", secondary_y=True, range=[0, 100])
    st.plotly_chart(fig_dual, use_container_width=True)

with col_l2:
    st.subheader("Reasons for Lost Files")
    mock_reasons = pd.DataFrame({
        'Reason': ['Not Doable', 'Not Doable', 'Not Interested', 'Not Interested', 'Pending Details / Document', 'Waiting to call back', 'Not interested (Sanction)', 'Line busy', 'Not reachable', 'Switched off'],
        'Stage': ['Lost from BP', 'Lost from Login', 'Lost from BP', 'Lost from Login', 'Lost from Login', 'Lost from Login', 'Lost from Sanction', 'Lost from BP', 'Lost from BP', 'Lost from BP'],
        'Count': [225, 136, 222, 47, 64, 16, 11, 9, 8, 1]
    })
    
    reason_totals = mock_reasons.groupby('Reason')['Count'].sum().reset_index()
    mock_reasons = mock_reasons.merge(reason_totals, on='Reason', suffixes=('', '_Total'))
    mock_reasons = mock_reasons.sort_values('Count_Total', ascending=True) 
    
    fig_reasons = px.bar(mock_reasons, y='Reason', x='Count', color='Stage', orientation='h', color_discrete_map={'Lost from BP': '#60a5fa', 'Lost from Login': '#ef4444', 'Lost from Sanction': '#fbbf24'})
    fig_reasons.update_layout(barmode='stack', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(gridcolor='#e2e8f0'), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig_reasons, use_container_width=True)
