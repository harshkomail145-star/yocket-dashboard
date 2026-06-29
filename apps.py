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
    /* Metric Card Styling */
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; border-top: 4px solid #4f46e5; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1); }
    /* Stylized section headers */
    .section-header { background-color: #ffffff; padding: 15px; border-radius: 8px; border-left: 5px solid #4f46e5; margin-top: 30px; margin-bottom: 15px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);}
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #e2e8f0; border-radius: 8px 8px 0 0; padding: 10px 20px; font-weight: 600;}
    .stTabs [aria-selected="true"] { background-color: #ffffff; border-bottom: 2px solid #4f46e5;}
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Fall 26 Command Center")

with st.sidebar:
    st.header("⚙️ Global Filters")
    selected_banks = st.multiselect("Select Bank Partners", ["Auxilo", "Credila", "Avanse", "SBI", "ICICI"], default=["Credila"])
    st.divider()
    st.caption("UI Mode: MOCK DATA 🟢")

# --- CREATE MAIN TABS ---
tab_overall, tab_branch = st.tabs(["🌐 Overall Performance", "📍 Branch Performance"])

# ==========================================
# TAB 2: BRANCH PERFORMANCE
# ==========================================
with tab_branch:
    st.subheader(f"Location-Wise Lead Distribution ({selected_banks[0]})")
    st.markdown("Top branches by total shared leads and their percentage of the total pie.")
    
    fig_branch_kpis = go.Figure()
    
    branches = [
        {"name": "📍 Bangalore", "val": "1,142", "pct": "40.0%"},
        {"name": "📍 Hyderabad", "val": "714", "pct": "25.0%"},
        {"name": "📍 Chennai", "val": "428", "pct": "15.0%"},
        {"name": "📍 Mumbai", "val": "285", "pct": "10.0%"},
        {"name": "📍 Delhi", "val": "143", "pct": "5.0%"},
        {"name": "📦 Others", "val": "143", "pct": "5.0%"}
    ]
    
    shapes = []
    annotations = []
    
    # 1. The Main Heading
    annotations.append(dict(
        x=0.5, y=1.15, xref='paper', yref='paper',
        text="<b>Lead Distribution Across Top Branches</b>",
        showarrow=False, font=dict(size=18, color="#1e293b"), xanchor='center'
    ))

    # 2. Draw the boxes and add perfectly centered text
    for i, b in enumerate(branches):
        x_center = (i + 0.5) / 6
        x_start = (i / 6) + 0.01
        x_end = ((i + 1) / 6) - 0.01
        
        # Add the physical box
        shapes.append(dict(
            type="rect", xref="paper", yref="paper",
            x0=x_start, y0=0, x1=x_end, y1=0.9,
            line=dict(color="#e2e8f0", width=2),
            fillcolor="#ffffff"
        ))
        
        # Branch Name (Now anchored strictly to the center)
        annotations.append(dict(
            x=x_center, y=0.70, xref="paper", yref="paper",
            text=f"{b['name']}", showarrow=False, font=dict(size=15, color="#64748b"),
            xanchor="center"
        ))
        
        # Big Number Value
        annotations.append(dict(
            x=x_center, y=0.45, xref="paper", yref="paper",
            text=f"<b>{b['val']}</b>", showarrow=False, font=dict(size=26, color="#1f4e71"),
            xanchor="center"
        ))
        
        # Percentage Share
        annotations.append(dict(
            x=x_center, y=0.20, xref="paper", yref="paper",
            text=f"<b>{b['pct']} Share</b>", showarrow=False, font=dict(size=13, color="#4f46e5"),
            xanchor="center"
        ))

    fig_branch_kpis.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="markers", marker_opacity=0, hoverinfo="none"))

    fig_branch_kpis.update_layout(
        shapes=shapes,
        annotations=annotations,
        xaxis=dict(visible=False, range=[0, 1]), 
        yaxis=dict(visible=False, range=[0, 1]), 
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=220,
        margin=dict(t=60, b=10, l=10, r=10) 
    )
    
    st.plotly_chart(fig_branch_kpis, use_container_width=True, config={'displayModeBar': True})
    
    st.divider()

# --- BRANCH COHORT PROGRESSION (MINI FUNNELS) ---
    st.subheader("Cohort Progression by Branch")
    st.markdown("Tracking the true funnel drop-off and stage-to-stage conversion rates for each location.")
    
    # Create a 2x3 grid for our 6 branch funnels
    fig_multi_funnel = make_subplots(
        rows=2, cols=3, 
        subplot_titles=["📍 Bangalore", "📍 Hyderabad", "📍 Chennai", "📍 Mumbai", "📍 Delhi", "📦 Others"],
        vertical_spacing=0.15,
        horizontal_spacing=0.08
    )
    
    # Mock data strictly mapped to your top KPI values
    branches_data = [
        {"name": "Bangalore", "vals": [1142, 850, 420, 210]},
        {"name": "Hyderabad", "vals": [714, 500, 250, 110]},
        {"name": "Chennai", "vals": [428, 300, 150, 70]},
        {"name": "Mumbai", "vals": [285, 200, 90, 40]},
        {"name": "Delhi", "vals": [143, 90, 40, 15]},
        {"name": "Others", "vals": [143, 100, 45, 20]}
    ]
    
    stages = ['Shared', 'Login', 'Sanction', 'PF']
    funnel_colors = ["#4f46e5", "#6366f1", "#818cf8", "#a5b4fc"]
    
    # Loop through the data and build a mini-funnel for each branch
    for i, b in enumerate(branches_data):
        row = (i // 3) + 1
        col = (i % 3) + 1
        
        fig_multi_funnel.add_trace(go.Funnel(
            name=b["name"],
            y=stages,
            x=b["vals"],
            textinfo="value+percent previous", # Magic command that adds the % conversion
            textposition="inside",
            marker={"color": funnel_colors, "line": {"width": [1, 1, 1, 1], "color": ["white", "white", "white", "white"]}},
            connector={"line": {"color": "#e2e8f0", "dash": "dot", "width": 2}}
        ), row=row, col=col)
        
    # Formatting to keep it clean and readable
    fig_multi_funnel.update_layout(
        height=650, # Made slightly taller to give the 2 rows room to breathe
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=60, b=40, l=20, r=20)
    )
    
    # Hide the bottom X-axis numbers (since they are inside the funnels) and bold the Y-axis stages
    fig_multi_funnel.update_xaxes(showticklabels=False)
    fig_multi_funnel.update_yaxes(showline=False, tickfont=dict(size=13, weight="bold"))
    
    st.plotly_chart(fig_multi_funnel, use_container_width=True)
    st.divider()

# --- COMPETITOR FLIGHT RISK MATRIX ---
    st.subheader("Competitor Flight Risk: Active Leads vs. Paid to Competitor")
    st.markdown("Grey = True Active. **Orange = Already Paid PF to Competitor.** Highlighting the highest % lost.")

    # 1. Setup a 1-Row, 3-Column subplot with a SHARED Y-axis
    fig_flight_risk = make_subplots(
        rows=1, cols=3, 
        shared_yaxes=True, 
        subplot_titles=("<b>BP Stage</b>", "<b>Login Stage</b>", "<b>Sanction Stage</b>"),
        horizontal_spacing=0.04
    )

    # Branches (We can keep the same order, or sort by worst offenders)
    branches_list = ["📦 Others", "📍 Delhi", "📍 Mumbai", "📍 Chennai", "📍 Hyderabad", "📍 Bangalore"]

    # Mock Data: [True Active, Paid Competitor]
    # BP Stage
    bp_active = [12, 16, 22, 30, 45, 60]
    bp_comp =   [1,  2,  5,  8,  10, 20] # 20 out of 80 total active in Bangalore have paid competitor
    
    # Login Stage
    log_active = [6, 8, 15, 20, 35, 50]
    log_comp =   [1, 1, 3,  9,  7,  13]
    
    # Sanction Stage
    san_active = [3, 5, 8,  12, 20, 25]
    san_comp =   [1, 1, 4,  6,  7,  15] # Bangalore losing heavily at Sanction

    def add_flight_risk_bars(active_data, comp_data, col_num, show_legend):
        # Calculate totals and percentages for the labels
        totals = [a + c for a, c in zip(active_data, comp_data)]
        comp_pcts = [f"{(c/t)*100:.0f}%" if t > 0 else "0%" for c, t in zip(comp_data, totals)]
        
        # True Active (Light, safe grey)
        fig_flight_risk.add_trace(go.Bar(
            name="True Workable", 
            y=branches_list, 
            x=active_data, 
            orientation='h',
            marker_color="#e2e8f0", 
            showlegend=show_legend,
            hoverinfo="x+name"
        ), row=1, col=col_num)
        
        # Paid to Competitor (Warning Orange) with the % label
        fig_flight_risk.add_trace(go.Bar(
            name="Paid Competitor", 
            y=branches_list, 
            x=comp_data, 
            orientation='h',
            marker_color="#f97316", # Vibrant warning orange
            showlegend=show_legend, 
            text=[f"{c} ({p})" for c, p in zip(comp_data, comp_pcts)], # Shows "20 (25%)"
            textposition="inside",
            insidetextfont=dict(color="white", weight="bold"),
            hoverinfo="x+name"
        ), row=1, col=col_num)

    # 2. Add the data
    add_flight_risk_bars(bp_active, bp_comp, col_num=1, show_legend=True)
    add_flight_risk_bars(log_active, log_comp, col_num=2, show_legend=False)
    add_flight_risk_bars(san_active, san_comp, col_num=3, show_legend=False)

    # 3. Clean up the layout
    fig_flight_risk.update_layout(
        barmode="stack", 
        height=400,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.15, xanchor="center", x=0.5),
        margin=dict(t=80, b=20, l=20, r=20)
    )

    fig_flight_risk.update_xaxes(showticklabels=False, showgrid=False)
    fig_flight_risk.update_yaxes(showgrid=False)
    
    st.plotly_chart(fig_flight_risk, use_container_width=True)
    st.divider()
    
# ==========================================
# TAB 1: OVERALL PERFORMANCE (All our previous code)
# ==========================================
with tab_overall:
    # --- SECTION 1: Y-O-Y METRICS ---
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

    # --- SECTION 2: FALL 26 M-o-M ---
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

    # --- SECTION 3: SHARED LEAD COHORT ---
    st.markdown('<div class="section-header"><h2>🧬 3. Shared Leads Funnel</h2></div>', unsafe_allow_html=True)
    totals = [2783, 2148, 1021, 504]
    custom_text = ["<b>Master Cohort</b>", "<b>Current:</b> 195 | <b>Lost:</b> 430", "<b>Current:</b> 453 | <b>Lost:</b> 643", "<b>Current:</b> 448 | <b>Lost:</b> 57"]
    fig_funnel = go.Figure(go.Funnel(y=stages, x=totals, text=custom_text, textposition="inside", textinfo="value+text+percent previous", marker={"color": ["#4f46e5", "#6366f1", "#818cf8", "#a5b4fc"], "line": {"width": [2, 2, 2, 2], "color": ["white", "white", "white", "white"]}}))
    fig_funnel.update_layout(margin={"t": 40, "b": 40}, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', yaxis=dict(showline=False, tickfont=dict(size=14, weight="bold")), xaxis=dict(showticklabels=False))
    st.plotly_chart(fig_funnel, use_container_width=True)

    # --- SECTION 4: ACTIVE AGING & LOST ANALYSIS ---
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
