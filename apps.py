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
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 8px 8px 0 0; padding: 8px 16px; font-weight: 600;}
    .stTabs [aria-selected="true"] { background-color: #ffffff; border-bottom: 2px solid #4f46e5;}
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

# --- 3. TABS SETUP ---
tab_yoy, tab_mom, tab_cohort, tab_aging, tab_lost = st.tabs([
    "📈 Y-o-Y Metrics", 
    "📅 Fall 26 M-o-M", 
    "🧬 Shared Lead Cohort", 
    "⏱️ Active Aging", 
    "🚨 Lost Analysis"
])
# ==========================================
# TAB 1: Y-O-Y METRICS (Source 1 & 2)
# ==========================================
with tab_yoy:
    st.subheader("A. Metric Comparison Fall 26 vs Fall 25")
    st.markdown("Year-over-Year (YoY) Performance & Growth")
    
    # --- 1. Top Level Metrics Chart (Replacing st.metrics) ---
    stages = ['Shared', 'Login', 'Sanction', 'PF']
    fall_25_data = [2067, 1752, 908, 467]
    fall_26_data = [2855, 2225, 1110, 588]
    yoy_growth = ['+38.1%', '+27.0%', '+22.2%', '+25.9%']

    fig_top_metrics = go.Figure()

    # Fall 25 Bars
    fig_top_metrics.add_trace(go.Bar(
        name='Fall 25 Till Date', 
        x=stages, 
        y=fall_25_data, 
        marker_color='#6a96b9', # Lighter blue from the image
        text=fall_25_data, 
        textposition='outside',
        textfont=dict(size=14, color='black')
    ))

    # Fall 26 Bars
    fig_top_metrics.add_trace(go.Bar(
        name='Fall 26 Till Date', 
        x=stages, 
        y=fall_26_data, 
        marker_color='#1f4e71', # Darker blue from the image
        text=fall_26_data, 
        textposition='outside',
        textfont=dict(size=14, color='black')
    ))

    # Add floating growth annotations above the bars
    growth_annotations = []
    for i, stage in enumerate(stages):
        y_max = max(fall_25_data[i], fall_26_data[i])
        growth_annotations.append(dict(
            x=stage,
            y=y_max + 350, # Offset to float above the bars
            text=f"<b>⬆ {yoy_growth[i]}</b><br><span style='font-size:11px'>YoY Growth</span>",
            showarrow=False,
            font=dict(size=14, color="black"),
            bgcolor="#f8fafc",
            bordercolor="#94a3b8", # Kept just the one bordercolor!
            borderwidth=1,
            borderpad=6
        ))

    fig_top_metrics.update_layout(
        barmode='group', 
        plot_bgcolor='rgba(0,0,0,0)', 
        yaxis=dict(gridcolor='#e2e8f0', range=[0, 3600]), # Added range to fit annotations
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        annotations=growth_annotations,
        margin=dict(t=80) # Extra top margin for legend and annotations
    )
    
    st.plotly_chart(fig_top_metrics, use_container_width=True)
    
    st.divider()
    
    # --- 2. YoY Monthly Logins ---
    st.subheader("Logins Fall 26 vs Fall 25")
    mock_yoy_monthly = pd.DataFrame({
        'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        'Fall 26': [219, 397, 444, 436, 377, 352],
        'Fall 25': [243, 297, 380, 322, 294, 231]
    })
    
    fig_yoy_bar = go.Figure(data=[
        go.Bar(name='Fall 26', x=mock_yoy_monthly['Month'], y=mock_yoy_monthly['Fall 26'], marker_color='#60a5fa', text=mock_yoy_monthly['Fall 26'], textposition='auto'),
        go.Bar(name='Fall 25', x=mock_yoy_monthly['Month'], y=mock_yoy_monthly['Fall 25'], marker_color='#ef4444', text=mock_yoy_monthly['Fall 25'], textposition='auto')
    ])
    fig_yoy_bar.update_layout(barmode='group', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(gridcolor='#e2e8f0'))
    st.plotly_chart(fig_yoy_bar, use_container_width=True)
# ==========================================
# TAB 2: FALL 26 M-o-M (Source 3)
# ==========================================
with tab_mom:
    st.subheader("Fall 26 - MoM metrics")
    
    # Generate mock grouped data
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    stages = ['shared', 'login', 'sanction', 'pf']
    
    mock_mom = pd.DataFrame({
        'Month': np.repeat(months, 4),
        'Stage': stages * 6,
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
    
    fig_mom = px.bar(mock_mom, x='Month', y='Value', color='Stage', barmode='group', 
                     text='Value', color_discrete_map=color_map)
    fig_mom.update_traces(textposition='outside')
    fig_mom.update_layout(plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(gridcolor='#e2e8f0'))
    st.plotly_chart(fig_mom, use_container_width=True)

# ==========================================
# TAB 3: SHARED LEAD COHORT (Source 4)
# ==========================================
with tab_cohort:
    st.subheader("Fall 26 Shared Leads Funnel")
    st.write("Tracking the progression and drop-off of the master Jan-Today shared cohort.")
    
    # Define the funnel data
    stages = ['Shared', 'Login', 'Sanction', 'PF']
    totals = [2783, 2148, 1021, 504]
    
    # Custom text to show Current and Lost counts inside the funnel
    custom_text = [
        "<b>Master Cohort</b>",
        "<b>Current:</b> 195 | <b>Lost:</b> 430",
        "<b>Current:</b> 453 | <b>Lost:</b> 643",
        "<b>Current:</b> 448 | <b>Lost:</b> 57"
    ]
    
    # Build the sexy funnel!
    fig_funnel = go.Figure(go.Funnel(
        y=stages,
        x=totals,
        text=custom_text,
        textposition="inside",
        # This tells Plotly to show the Number + Our Custom Text + The Conversion %
        textinfo="value+text+percent previous", 
        # Using a sleek color gradient matching your app's indigo theme
        marker={
            "color": ["#4f46e5", "#6366f1", "#818cf8", "#a5b4fc"],
            "line": {"width": [2, 2, 2, 2], "color": ["white", "white", "white", "white"]}
        },
        connector={"line": {"color": "#e2e8f0", "dash": "dot", "width": 2}}
    ))
    
    fig_funnel.update_layout(
        margin={"t": 40, "b": 40},
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(title_text="", showline=False, tickfont=dict(size=14, weight="bold")),
        xaxis=dict(showticklabels=False) # Hide X axis numbers since they are inside the funnel
    )
    
    st.plotly_chart(fig_funnel, use_container_width=True)
# ==========================================
# TAB 4: ACTIVE AGING & COMPETITOR LOSS (Source 5 & 6)
# ==========================================
with tab_aging:
    st.subheader("Active Workable Leads & Aging Matrix")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### BP Stage")
        st.metric("BP Active Leads", "100")
        st.metric("Paid PF to Competitor", "20", "-20", delta_color="inverse")
        st.info("**Active Workable: 80**\n\n🟢 Less than 7 Days: 34\n\n🔴 More than 7 Days: 46")
        
    with col2:
        st.markdown("### Login Stage")
        st.metric("Login Active Leads", "70")
        st.metric("Paid PF to Competitor", "15", "-15", delta_color="inverse")
        st.info("**Active Workable: 55**\n\n🟢 Less than 7 Days: 30\n\n🔴 More than 7 Days: 25")
        
    with col3:
        st.markdown("### Sanction Stage")
        st.metric("Sanction Active Leads", "60")
        st.metric("Paid PF to Competitor", "20", "-20", delta_color="inverse")
        st.info("**Active Workable: 40**\n\n🟢 Less than 7 Days: 27\n\n🔴 More than 7 Days: 13")

# ==========================================
# TAB 5: LOST ANALYSIS (Source 7 & 8)
# ==========================================
with tab_lost:
    
    # Chart 1: Lost Potential (Dual Axis)
    st.subheader("Lost Potential (%) vs Total Files")
    
    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    
    stages = ['Lost from BP', 'Lost from Login', 'Lost from Sanction']
    total_files = [200, 300, 100]
    went_ahead = [145, 204, 85]
    lost_potential = [72.5, 68.0, 85.0]
    
    # Add Bars
    fig_dual.add_trace(go.Bar(name='Total Files', x=stages, y=total_files, marker_color='#60a5fa'), secondary_y=False)
    fig_dual.add_trace(go.Bar(name='Went Ahead in Other Banks', x=stages, y=went_ahead, marker_color='#ef4444'), secondary_y=False)
    
    # Add Line
    fig_dual.add_trace(go.Scatter(name='% Lost Potential', x=stages, y=lost_potential, mode='lines+markers+text', 
                                  marker=dict(size=12, color='#fbbf24'), line=dict(width=4, color='#fbbf24'),
                                  text=[f"{x}%" for x in lost_potential], textposition="top center", textfont=dict(weight='bold')), 
                       secondary_y=True)
    
    fig_dual.update_layout(barmode='group', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=-0.15, x=0.2))
    fig_dual.update_yaxes(title_text="Number of Files", secondary_y=False, gridcolor='#e2e8f0')
    fig_dual.update_yaxes(title_text="% Lost Potential", secondary_y=True, range=[0, 100])
    
    st.plotly_chart(fig_dual, use_container_width=True)
    
    st.divider()
    
    # Chart 2: Lost Reasons
    st.subheader("Reasons for Lost Files Broken Down by Stage")
    
    mock_reasons = pd.DataFrame({
        'Reason': ['Not Doable', 'Not Doable', 'Not Interested', 'Not Interested', 'Pending Details / Document', 'Waiting to call back', 'Not interested (Sanction)', 'Line busy', 'Not reachable', 'Switched off'],
        'Stage': ['Lost from BP', 'Lost from Login', 'Lost from BP', 'Lost from Login', 'Lost from Login', 'Lost from Login', 'Lost from Sanction', 'Lost from BP', 'Lost from BP', 'Lost from BP'],
        'Count': [225, 136, 222, 47, 64, 16, 11, 9, 8, 1]
    })
    
    # Calculate totals for sorting
    reason_totals = mock_reasons.groupby('Reason')['Count'].sum().reset_index()
    mock_reasons = mock_reasons.merge(reason_totals, on='Reason', suffixes=('', '_Total'))
    mock_reasons = mock_reasons.sort_values('Count_Total', ascending=True) # Ascending for horizontal bar
    
    fig_reasons = px.bar(mock_reasons, y='Reason', x='Count', color='Stage', orientation='h',
                         color_discrete_map={'Lost from BP': '#60a5fa', 'Lost from Login': '#ef4444', 'Lost from Sanction': '#fbbf24'})
    
    fig_reasons.update_layout(barmode='stack', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(gridcolor='#e2e8f0'))
    st.plotly_chart(fig_reasons, use_container_width=True)
