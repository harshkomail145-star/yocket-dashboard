import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="Fall 26 Analytics", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; border-top: 4px solid #4f46e5; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1); }
    .section-header { background-color: #ffffff; padding: 15px; border-radius: 8px; border-left: 5px solid #4f46e5; margin-top: 30px; margin-bottom: 15px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);}
    
    /* --- THE ULTIMATE PRINT CSS NUKE --- */
    @media print {
        /* 1. Hide the Streamlit UI elements */
        header, footer, [data-testid="stSidebar"], [data-testid="stHeader"] { 
            display: none !important; 
        }
        
        /* 2. Force ALL hidden Streamlit containers to unroll and show their full height */
        html, body, .stApp, .main, .block-container, 
        [data-testid="stAppViewContainer"], 
        [data-testid="stMain"], 
        [data-testid="stMainBlockContainer"] {
            height: auto !important;
            min-height: 100% !important;
            overflow: visible !important;
            position: static !important;
            display: block !important;
        }
        
        /* 3. Stop the printer from slicing your charts in half */
        .stPlotlyChart, [data-testid="stElementContainer"] {
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
st.title("📊 Fall 26 Command Center")

# --- EXPORT BANNER ---
st.info("💡 **Want to download this report?** Press `Ctrl + P` (or `Cmd + P` on Mac) to use your browser's **Save as PDF** feature. It will capture all charts and layouts perfectly!")

with st.sidebar:
    st.header("⚙️ Global Filters")
    selected_banks = st.multiselect("Select Bank Partners", ["Auxilo", "Credila", "Avanse", "SBI", "ICICI"], default=["Credila"])
    st.divider()
    st.caption("UI Mode: MOCK DATA 🟢")

# ==========================================
# SECTION 1: Y-O-Y METRICS
# ==========================================
st.markdown('<div class="section-header"><h2>📈 1. Y-o-Y Metrics (Fall 26 vs Fall 25)</h2></div>', unsafe_allow_html=True)

stages = ['Shared', 'Login', 'Sanction', 'PF']
fall_25_data = [2067, 1752, 908, 467]
fall_26_data = [2855, 2225, 1110, 588]
yoy_growth = ['+38.1%', '+27.0%', '+22.2%', '+25.9%']

fig_top_metrics = go.Figure()
fig_top_metrics.add_trace(go.Bar(name='Fall 25', x=stages, y=fall_25_data, marker_color='#6a96b9', text=fall_25_data, textposition='outside', textfont=dict(size=14, color='black')))
fig_top_metrics.add_trace(go.Bar(name='Fall 26', x=stages, y=fall_26_data, marker_color='#1f4e71', text=fall_26_data, textposition='outside', textfont=dict(size=14, color='black')))

growth_annotations = []
for i, stage in enumerate(stages):
    y_max = max(fall_25_data[i], fall_26_data[i])
    growth_annotations.append(dict(
        x=stage, y=y_max + 350, 
        text=f"<b>⬆ {yoy_growth[i]}</b><br><span style='font-size:11px'>YoY Growth</span>",
        showarrow=False, font=dict(size=14, color="black"), bgcolor="#f8fafc", bordercolor="#94a3b8", borderwidth=1, borderpad=6
    ))

fig_top_metrics.update_layout(barmode='group', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(gridcolor='#e2e8f0', range=[0, 3600]), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5), annotations=growth_annotations, margin=dict(t=80))
st.plotly_chart(fig_top_metrics, use_container_width=True)

# ==========================================
# SECTION 2: FALL 26 M-o-M 
# ==========================================
st.markdown('<div class="section-header"><h2>📅 2. Fall 26 M-o-M Logins</h2></div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)

with col1:
    st.subheader("YoY Monthly Logins")
    mock_yoy_monthly = pd.DataFrame({'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'], 'Fall 26': [219, 397, 444, 436, 377, 352], 'Fall 25': [243, 297, 380, 322, 294, 231]})
    fig_yoy_bar = go.Figure(data=[
        go.Bar(name='Fall 26', x=mock_yoy_monthly['Month'], y=mock_yoy_monthly['Fall 26'], marker_color='#60a5fa', text=mock_yoy_monthly['Fall 26'], textposition='auto'),
        go.Bar(name='Fall 25', x=mock_yoy_monthly['Month'], y=mock_yoy_monthly['Fall 25'], marker_color='#ef4444', text=mock_yoy_monthly['Fall 25'], textposition='auto')
    ])
    fig_yoy_bar.update_layout(barmode='group', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(gridcolor='#e2e8f0'), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig_yoy_bar, use_container_width=True)

with col2:
    st.subheader("MoM Progression by Stage")
    months, stages_mom = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'], ['shared', 'login', 'sanction', 'pf']
    mock_mom = pd.DataFrame({
        'Month': np.repeat(months, 4), 'Stage': stages_mom * 6,
        'Value': [265, 219, 85, 36, 575, 397, 185, 66, 576, 444, 219, 93, 535, 437, 255, 126, 484, 377, 205, 146, 447, 352, 162, 121]
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
totals = [2783, 2148, 1021, 504]
custom_text = ["<b>Master Cohort</b>", "<b>Current:</b> 195 | <b>Lost:</b> 430", "<b>Current:</b> 453 | <b>Lost:</b> 643", "<b>Current:</b> 448 | <b>Lost:</b> 57"]
fig_funnel = go.Figure(go.Funnel(y=stages, x=totals, text=custom_text, textposition="inside", textinfo="value+text+percent previous", marker={"color": ["#4f46e5", "#6366f1", "#818cf8", "#a5b4fc"], "line": {"width": [2, 2, 2, 2], "color": ["white", "white", "white", "white"]}}))
fig_funnel.update_layout(margin={"t": 40, "b": 40}, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', yaxis=dict(showline=False, tickfont=dict(size=14, weight="bold")), xaxis=dict(showticklabels=False))
st.plotly_chart(fig_funnel, use_container_width=True)

# ==========================================
# SECTION 4: ACTIVE AGING & LOST ANALYSIS
# ==========================================
st.markdown('<div class="section-header"><h2>🚨 4. Lost Potential Analysis</h2></div>', unsafe_allow_html=True)
col_l1, col_l2 = st.columns(2)

with col_l1:
    st.subheader("Lost Potential (%) vs Total Files")
    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    stages_lost, total_files, went_ahead, lost_potential = ['Lost from BP', 'Lost from Login', 'Lost from Sanction'], [200, 300, 100], [145, 204, 85], [72.5, 68.0, 85.0]
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
    mock_reasons = mock_reasons.merge(reason_totals, on='Reason', suffixes=('', '_Total')).sort_values('Count_Total', ascending=True) 
    fig_reasons = px.bar(mock_reasons, y='Reason', x='Count', color='Stage', orientation='h', color_discrete_map={'Lost from BP': '#60a5fa', 'Lost from Login': '#ef4444', 'Lost from Sanction': '#fbbf24'})
    fig_reasons.update_layout(barmode='stack', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(gridcolor='#e2e8f0'), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig_reasons, use_container_width=True)
