import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 1. PAGE CONFIG & MODERN THEME STYLING
# ==========================================
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

# ==========================================
# 2. GLOBAL FILTERS (SIDEBAR)
# ==========================================
with st.sidebar:
    st.header("⚙️ Global Filters")
    selected_banks = st.multiselect("Select Bank Partners", ["Auxilo", "Credila", "Avanse", "SBI", "ICICI"], default=["Credila"])
    st.divider()
    st.caption("UI Mode: HYBRID DATA ENGINE 🟢")

# Initialize our Top-Level Navigational Tabs
tab_overall, tab_branch, tab_compare, tab_adapt, tab_bp_login, tab_log_san, tab_san_pf = st.tabs([
    "🌐 Overall Performance", 
    "📍 Branch Performance", 
    "🔄 Branch Comparison", 
    "💻 System Adaptability",
    "🔍 BP to Login",
    "📝 Login to Sanction",
    "✅ Sanction to PF"
])
# ==========================================
# TAB 1: OVERALL PERFORMANCE
# ==========================================
with tab_overall:
    # --- SECTION 1: Y-O-Y COMPARISONS (SIDE-BY-SIDE) ---
    st.markdown('<div class="section-header"><h2>📈 1. Y-o-Y Performance & Monthly Logins</h2></div>', unsafe_allow_html=True)
    
    st.text_area(
        label="Notes", 
        placeholder="Type your insights, talking points, or action items here...", 
        label_visibility="collapsed", 
        key="note_yoy_metrics" 
    )

    col1, col2 = st.columns(2)

    # Unified Palette
    COLOR_FALL_26 = "#1e40af" # Primary Dark Blue
    COLOR_FALL_25 = "#93c5fd" # Secondary Light Blue

    with col1:
        st.subheader("Y-o-Y Metrics (Fall 26 vs Fall 25)")
        stages = ['Shared', 'Login', 'Sanction', 'PF']
        fall_26_data = [2855, 2225, 1110, 588]
        fall_25_data = [2067, 1752, 908, 467]
        yoy_growth = ['+38.1%', '+27.0%', '+22.2%', '+25.9%']

        fig_top_metrics = go.Figure()
        # Fall 26 First
        fig_top_metrics.add_trace(go.Bar(name="Fall '26", x=stages, y=fall_26_data, marker_color=COLOR_FALL_26, text=fall_26_data, textposition='outside', textfont=dict(size=14, color='black')))
        # Fall 25 Second
        fig_top_metrics.add_trace(go.Bar(name="Fall '25", x=stages, y=fall_25_data, marker_color=COLOR_FALL_25, text=fall_25_data, textposition='outside', textfont=dict(size=14, color='black')))

        growth_annotations = []
        for i, stage in enumerate(stages):
            y_max = max(fall_25_data[i], fall_26_data[i])
            growth_annotations.append(dict(
                x=stage, y=y_max + 550, 
                text=f"<b>⬆ {yoy_growth[i]}</b><br><span style='font-size:11px'>YoY Growth</span>",
                showarrow=False, font=dict(size=14, color="black"), bgcolor="#f8fafc", bordercolor="#94a3b8", borderwidth=1, borderpad=6
            ))

        fig_top_metrics.update_layout(
            barmode='group', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(gridcolor='#e2e8f0', range=[0, 4200]), 
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5), 
            annotations=growth_annotations, margin=dict(t=80)
        )
        st.plotly_chart(fig_top_metrics, use_container_width=True)

    with col2:
        st.subheader("YoY Monthly Logins")
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        fall_26_logins = [219, 397, 444, 436, 377, 352]
        fall_25_logins = [243, 297, 380, 322, 294, 231]
        
        # Calculated from the raw data: (Fall26 - Fall25) / Fall25
        mom_growth = ['-9.9%', '+33.7%', '+16.8%', '+35.4%', '+28.2%', '+52.4%']

        fig_yoy_bar = go.Figure()
        # Fall 26 First
        fig_yoy_bar.add_trace(go.Bar(name="Fall '26", x=months, y=fall_26_logins, marker_color=COLOR_FALL_26, text=fall_26_logins, textposition='outside', textfont=dict(size=14, color='black')))
        # Fall 25 Second
        fig_yoy_bar.add_trace(go.Bar(name="Fall '25", x=months, y=fall_25_logins, marker_color=COLOR_FALL_25, text=fall_25_logins, textposition='outside', textfont=dict(size=14, color='black')))

        # Added the identical floating boxes for MoM
        mom_annotations = []
        for i, month in enumerate(months):
            y_max = max(fall_26_logins[i], fall_25_logins[i])
            # Determine icon based on growth/decline
            icon = "⬇" if "-" in mom_growth[i] else "⬆"
            
            mom_annotations.append(dict(
                x=month, y=y_max + 80, # Offset scaled down because this Y-axis is much smaller
                text=f"<b>{icon} {mom_growth[i]}</b><br><span style='font-size:11px'>Growth</span>",
                showarrow=False, font=dict(size=13, color="black"), bgcolor="#f8fafc", bordercolor="#94a3b8", borderwidth=1, borderpad=6
            ))

        fig_yoy_bar.update_layout(
            barmode='group', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(gridcolor='#e2e8f0', range=[0, 600]), # Increased range to 600 to fit boxes
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5), 
            annotations=mom_annotations, margin=dict(t=80)
        )
        st.plotly_chart(fig_yoy_bar, use_container_width=True)
    
    st.divider()
# --- SECTION 2: FALL 26 M-O-M PROGRESSION ---
    st.markdown('<div class="section-header"><h2>📅 2. Fall 26 M-o-M Progression by Stage</h2></div>', unsafe_allow_html=True)
    st.markdown("Tracking how the current Fall '26 pipeline is converting through all stages month-over-month.")
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    stages_mom = ['shared', 'login', 'sanction', 'pf']
    
    mock_mom = pd.DataFrame({
        'Month': np.repeat(months, 4), 
        'Stage': stages_mom * 6,
        'Value': [265, 219, 85, 36, 575, 397, 185, 66, 576, 444, 219, 93, 535, 437, 255, 126, 484, 377, 205, 146, 447, 352, 162, 121]
    })
    
    # Keeping distinct but using cute, soft pastel colors for the different stages
    color_map = {
        'shared': '#a78bfa',   # Soft Pastel Lavender/Purple
        'login': '#fda4af',    # Soft Pastel Rose/Pink
        'sanction': '#fef08a', # Soft Pastel Yellow
        'pf': '#a7f3d0'        # Soft Pastel Mint Green
    }
    
    fig_mom = px.bar(
        mock_mom, x='Month', y='Value', color='Stage', 
        barmode='group', text='Value', color_discrete_map=color_map
    )
    
    fig_mom.update_traces(textposition='outside', textfont=dict(size=12, color="black"))
    
    fig_mom.update_layout(
        height=380, margin=dict(t=40, b=20, l=20, r=20),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(gridcolor='#e2e8f0', range=[0, 700]), # Added range so the top numbers don't clip
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5, title=None)
    )
    st.plotly_chart(fig_mom, use_container_width=True)
    
    st.divider()
   # --- SECTION 3: SHARED LEAD COHORT FUNNEL ---
    st.markdown('<div class="section-header"><h2>🧬 3. Shared Leads Pipeline</h2></div>', unsafe_allow_html=True)
    # Legend for the color-coded dots so no text labels are needed inside the chart
    st.markdown("Left-to-Right pipeline tracking active volumes, drop-offs, and true stage-to-stage conversion. <br><span style='color:#a7f3d0; font-size:18px'>●</span> <b>Current (Active)</b> &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#fca5a5; font-size:18px'>●</span> <b>Lost (Dropped)</b>", unsafe_allow_html=True)
    
    stages = ['Shared (BP)', 'Login Stage', 'Sanction Stage', 'PF Paid']
    totals = [2783, 2148, 1021, 504]
    
    currents = [215, 317, 157, 504]
    losts = [420, 810, 360, 0]
    
    # Clean, large center numbers for "Reached" (No words)
    custom_text = [
        "<b style='font-size: 32px; color: white;'>2,783</b>",
        "<b style='font-size: 32px; color: white;'>2,148</b>",
        "<b style='font-size: 32px; color: white;'>1,021</b>",
        "<b style='font-size: 32px; color: white;'>504</b>"
    ]
    
    fig_funnel = go.Figure(go.Funnel(
        orientation='v', 
        x=stages, y=totals, text=custom_text, textposition="inside", textinfo="text",
        marker={"color": ["#4f46e5", "#6366f1", "#818cf8", "#a5b4fc"], "line": {"width": [2, 2, 2, 2], "color": ["white", "white", "white", "white"]}},
        connector={"line": {"color": "#e2e8f0", "dash": "solid", "width": 2}, "fillcolor": "rgba(226, 232, 240, 0.4)"}
    ))
    
    # Plotly funnels center the bars at Y=0. 
    # Top edge is +(total/2), bottom edge is -(total/2).
    for i, stage in enumerate(stages):
        top_y = (totals[i] / 2) * 0.70     # Pushed safely into the upper half
        bottom_y = -(totals[i] / 2) * 0.70 # Pushed safely into the lower half
        
        # Top-Left: Current Active (Mint Green Dot + Number)
        fig_funnel.add_annotation(
            x=stage, y=top_y, 
            text=f"<span style='color:#a7f3d0; font-size:16px'>●</span> <b style='color:white; font-size:15px'>{currents[i]}</b>", 
            showarrow=False, xanchor='right', xshift=-45 # Pushes it precisely to the left of the center number
        )
        
        # Bottom-Left: Lost Dropped (Soft Red Dot + Number)
        if losts[i] > 0:
            fig_funnel.add_annotation(
                x=stage, y=bottom_y,
                text=f"<span style='color:#fca5a5; font-size:16px'>●</span> <b style='color:white; font-size:15px'>{losts[i]}</b>", 
                showarrow=False, xanchor='right', xshift=-45 
            )

    # Conversion arrows between stages hovering perfectly above the connectors
    fig_funnel.add_annotation(x=0.5, y=1.05, xref="x", yref="paper", text="<b>77.2% ➔</b>", showarrow=False, font=dict(size=14, color="#4f46e5"), bgcolor="#ffffff", bordercolor="#e2e8f0", borderwidth=1, borderpad=5)
    fig_funnel.add_annotation(x=1.5, y=1.05, xref="x", yref="paper", text="<b>47.5% ➔</b>", showarrow=False, font=dict(size=14, color="#4f46e5"), bgcolor="#ffffff", bordercolor="#e2e8f0", borderwidth=1, borderpad=5)
    fig_funnel.add_annotation(x=2.5, y=1.05, xref="x", yref="paper", text="<b>49.4% ➔</b>", showarrow=False, font=dict(size=14, color="#4f46e5"), bgcolor="#ffffff", bordercolor="#e2e8f0", borderwidth=1, borderpad=5)
    
    fig_funnel.update_layout(
        height=400, margin={"t": 70, "b": 40, "l": 20, "r": 20},
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', 
        xaxis=dict(showline=False, tickfont=dict(size=15, weight="bold", color="#1e293b")),
        yaxis=dict(showticklabels=False, showgrid=False, range=[-1600, 1600]) # Locking the axis prevents the dots from drifting
    )
    st.plotly_chart(fig_funnel, use_container_width=True)
    # --- SECTION 4: ACTIVE PIPELINE HEALTH (COMPACT STACKED BAR) ---
    st.markdown('<div class="section-header"><h2>⏱️ 4. Active Pipeline Health</h2></div>', unsafe_allow_html=True)
    st.markdown("A macro view of your active pipeline. Breaking down healthy leads vs. aging bottlenecks vs. competitor leakage.")

    stages_health = ["<b>BP Stage</b><br>100 Leads", "<b>Login Stage</b><br>70 Leads", "<b>Sanction Stage</b><br>60 Leads"]

    under_7_vals = [34, 30, 27]
    over_7_vals  = [46, 25, 13]
    comp_vals    = [20, 15, 20]

    totals_health = [100, 70, 60]
    under_7_pcts = [f"{(v/t)*100:.0f}%" for v, t in zip(under_7_vals, totals_health)]
    over_7_pcts  = [f"{(v/t)*100:.0f}%" for v, t in zip(over_7_vals, totals_health)]
    comp_pcts    = [f"{(v/t)*100:.0f}%" for v, t in zip(comp_vals, totals_health)]

    fig_health_bar = go.Figure()

    color_under = "#a7f3d0" # Soft Sage Green
    color_over  = "#fed7aa" # Soft Peach Orange
    color_comp  = "#9f1239" # Deep Brick Red
    
    fig_health_bar.add_trace(go.Bar(
        name="< 7 Days (Active)", y=stages_health, x=under_7_vals, orientation='h', marker_color=color_under,
        text=[f"{v} ({p})" for v, p in zip(under_7_vals, under_7_pcts)],
        textposition="inside", insidetextanchor="middle", insidetextfont=dict(color="#0f172a", size=14, weight="bold"), hoverinfo="name+x"
    ))

    fig_health_bar.add_trace(go.Bar(
        name="> 7 Days (Aging)", y=stages_health, x=over_7_vals, orientation='h', marker_color=color_over,
        text=[f"{v} ({p})" for v, p in zip(over_7_vals, over_7_pcts)],
        textposition="inside", insidetextanchor="middle", insidetextfont=dict(color="#0f172a", size=14, weight="bold"), hoverinfo="name+x"
    ))

    fig_health_bar.add_trace(go.Bar(
        name="Lost to Competitor", y=stages_health, x=comp_vals, orientation='h', marker_color=color_comp,
        text=[f"{v} ({p})" for v, p in zip(comp_vals, comp_pcts)],
        textposition="inside", insidetextanchor="middle", insidetextfont=dict(color="white", size=14, weight="bold"), hoverinfo="name+x"
    ))

    fig_health_bar.update_layout(
        barmode="stack", height=320, margin=dict(t=40, b=20, l=20, r=20),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5),
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False, tickfont=dict(size=15, color="#1e293b"), autorange="reversed") 
    )
    st.plotly_chart(fig_health_bar, use_container_width=True)
    st.divider()

    # --- SECTION 5: LOSING THE ACTIVE PROSPECTS (PIPELINE SPLIT BAR) ---
    st.markdown('<div class="section-header"><h2>💸 5. Losing The Active Prospects</h2></div>', unsafe_allow_html=True)
    st.markdown("Where our workable leads are currently sitting (Exclusive vs. Flight Risk).")

    stages_loss = ["<b>Login Stage</b><br>60 Active Leads", "<b>BP Stage</b><br>80 Active Leads"]

    exc_vals = [30, 40]
    exc_pcts = ["50%", "50%"]
    clog_vals = [0, 30] 
    clog_pcts = ["0%", "38%"]
    csan_vals = [30, 10]
    csan_pcts = ["50%", "12%"]

    fig_loss_bar = go.Figure()

    fig_loss_bar.add_trace(go.Bar(
        name="✅ Exclusive (Safe)", y=stages_loss, x=exc_vals, orientation='h', marker_color=color_under,
        text=[f"{v} ({p})" if v > 0 else "" for v, p in zip(exc_vals, exc_pcts)],
        textposition="inside", insidetextanchor="middle", insidetextfont=dict(color="#0f172a", size=14, weight="bold"), hoverinfo="name+x"
    ))

    fig_loss_bar.add_trace(go.Bar(
        name="⚠️ In Competitor Login", y=stages_loss, x=clog_vals, orientation='h', marker_color=color_over,
        text=[f"{v} ({p})" if v > 0 else "" for v, p in zip(clog_vals, clog_pcts)],
        textposition="inside", insidetextanchor="middle", insidetextfont=dict(color="#0f172a", size=14, weight="bold"), hoverinfo="name+x"
    ))

    fig_loss_bar.add_trace(go.Bar(
        name="🚨 In Competitor Sanction", y=stages_loss, x=csan_vals, orientation='h', marker_color=color_comp,
        text=[f"{v} ({p})" if v > 0 else "" for v, p in zip(csan_vals, csan_pcts)],
        textposition="inside", insidetextanchor="middle", insidetextfont=dict(color="white", size=14, weight="bold"), hoverinfo="name+x"
    ))

    fig_loss_bar.update_layout(
        barmode="stack", height=280, margin=dict(t=40, b=20, l=20, r=20),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5),
        xaxis=dict(showgrid=False, showticklabels=False), 
        yaxis=dict(showgrid=False, tickfont=dict(size=15, color="#1e293b"))
    )
    st.plotly_chart(fig_loss_bar, use_container_width=True)
    st.divider()

    # --- SECTION 6: LOST POTENTIAL ANALYSIS ---
    st.markdown('<div class="section-header"><h2>🚨 6. Lost Potential Analysis</h2></div>', unsafe_allow_html=True)
    
    # --- PART A: COMPETITOR PROGRESSION (STRETCHED FULL WIDTH) ---
    st.subheader("Flight Risk: Where are they in the Competitor's Funnel?")
    st.markdown("Out of the total files lost at each stage, this tracks how many went to a competitor and **exactly what stage the competitor has reached with them**.")

    # Data structuring (Totals: BP=200, Login=300, Sanction=100)
    stages_lost = ["<b>Lost from Sanction</b><br>(100 Total)", "<b>Lost from Login</b><br>(300 Total)", "<b>Lost from BP</b><br>(200 Total)"]
    bar_totals = [100, 300, 200]
    
    # The math: Total Lost = True Dead + Comp Login + Comp Sanction + Comp PF
    true_dead = [15, 96, 55]    # Leads that dropped entirely and did NOT go to a competitor
    comp_login = [0, 0, 45]     # Competitor is currently at Login (Only possible if lost from BP)
    comp_sanc = [0, 104, 50]    # Competitor is currently at Sanction
    comp_pf = [85, 100, 50]     # Competitor has already collected PF

    # Potential Loss Calculation: (Total Volume - True Dead Volume) / Total Volume
    # Sanction: (100 - 15) / 100 = 85.0%
    # Login: (300 - 96) / 300 = 68.0%
    # BP: (200 - 55) / 200 = 72.5%
    potential_loss_pcts = ["85.0%", "68.0%", "72.5%"]

    fig_flight = go.Figure()

    # 1. True Dead (Grey - untouched by competitor)
    fig_flight.add_trace(go.Bar(
        name="True Dead (No Competitor Action)", y=stages_lost, x=true_dead, orientation='h', marker_color="#e2e8f0",
        text=[f"{v}" if v > 0 else "" for v in true_dead], 
        textposition="inside", insidetextanchor="middle", insidetextfont=dict(color="#475569", weight="bold")
    ))
    # 2. Competitor Login (Light Orange)
    fig_flight.add_trace(go.Bar(
        name="In Competitor Login", y=stages_lost, x=comp_login, orientation='h', marker_color="#fdba74",
        text=[f"{v}" if v > 0 else "" for v in comp_login], 
        textposition="inside", insidetextanchor="middle", insidetextfont=dict(color="#9a3412", weight="bold")
    ))
    # 3. Competitor Sanction (Dark Orange)
    fig_flight.add_trace(go.Bar(
        name="In Competitor Sanction", y=stages_lost, x=comp_sanc, orientation='h', marker_color="#f97316",
        text=[f"{v}" if v > 0 else "" for v in comp_sanc], 
        textposition="inside", insidetextanchor="middle", insidetextfont=dict(color="white", weight="bold")
    ))
    # 4. Competitor PF Paid (Red/Crimson)
    fig_flight.add_trace(go.Bar(
        name="Competitor PF Paid (Fully Lost)", y=stages_lost, x=comp_pf, orientation='h', marker_color="#9f1239",
        text=[f"{v}" if v > 0 else "" for v in comp_pf], 
        textposition="inside", insidetextanchor="middle", insidetextfont=dict(color="white", weight="bold")
    ))

    # Aesthetically adding Potential Loss summaries dynamically right at the tip of each bar
    for i, stage in enumerate(stages_lost):
        fig_flight.add_annotation(
            x=bar_totals[i], y=stage,
            text=f"<span style='color:#64748b; font-size:11px; font-weight:normal;'>Potential Loss</span><br><b style='font-size:16px; color:#9f1239;'>⚠️ {potential_loss_pcts[i]}</b>",
            showarrow=False, xanchor="left", xshift=15, align="left"
        )

    fig_flight.update_layout(
        barmode="stack", height=320, margin=dict(t=40, b=20, l=20, r=100), # Increased right margin to protect text labels
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5),
        xaxis=dict(showgrid=False, showticklabels=False, range=[0, 390]), # Locked range to 390 to prevent overlapping
        yaxis=dict(showgrid=False, tickfont=dict(size=14, color="#1e293b"))
    )
    st.plotly_chart(fig_flight, use_container_width=True)

    st.divider()

    # --- PART B: REASONS FOR LOSS (BROKEN DOWN BY STAGE) ---
    st.subheader("Reason for Loss Matrix")
    st.markdown("Isolated breakdown of why files were dropped at each specific stage.")

    col_r1, col_r2, col_r3 = st.columns(3)

    # Helper function to generate standardized horizontal bar charts for reasons
    def plot_reason_bar(reasons, counts, color):
        df = pd.DataFrame({'Reason': reasons, 'Count': counts}).sort_values('Count', ascending=True)
        fig = go.Figure(go.Bar(
            y=df['Reason'], x=df['Count'], orientation='h', marker_color=color,
            text=df['Count'], textposition='outside', textfont=dict(weight="bold", color="#1e293b")
        ))
        fig.update_layout(
            height=280, margin=dict(t=20, b=20, l=10, r=40), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showgrid=False, tickfont=dict(weight="bold", color="#475569"))
        )
        return fig

    with col_r1:
        st.markdown("**1. Lost from BP Stage**")
        bp_reasons = ['Not Interested', 'Not Doable', 'Line Busy', 'Not Reachable', 'Switched Off']
        bp_counts = [110, 65, 12, 8, 5]
        st.plotly_chart(plot_reason_bar(bp_reasons, bp_counts, '#94a3b8'), use_container_width=True)

    with col_r2:
        st.markdown("**2. Lost from Login Stage**")
        login_reasons = ['Pending Docs', 'Not Doable', 'Rate/ROI Issue', 'Not Interested']
        login_counts = [140, 85, 45, 30]
        st.plotly_chart(plot_reason_bar(login_reasons, login_counts, '#64748b'), use_container_width=True)

    with col_r3:
        st.markdown("**3. Lost from Sanction Stage**")
        sanc_reasons = ['Rate/ROI Issue', 'Disbursed Elsewhere', 'Not Interested', 'Processing Fee Issue']
        sanc_counts = [42, 35, 15, 8]
        st.plotly_chart(plot_reason_bar(sanc_reasons, sanc_counts, '#475569'), use_container_width=True)

# ==========================================
# TAB 5: BP TO LOGIN DEEP DIVE
# ==========================================
with tab_bp_login:
    # --- TOP CARDS: VOLUME DISTRIBUTION ---
    st.markdown('<div class="section-header"><h2>🗂️ BP Stage Lead Distribution</h2></div>', unsafe_allow_html=True)
    
    # Mock data for top 5 branches + Others
    top_branches = ["Bangalore", "Hyderabad", "Chennai", "Mumbai", "Delhi", "Others"]
    bp_vols = [1142, 714, 428, 285, 143, 143]
    bp_pcts = ["40.0%", "25.0%", "15.0%", "10.0%", "5.0%", "5.0%"]
    
    # Generate metric cards in a clean row
    card_cols = st.columns(6)
    for i, col in enumerate(card_cols):
        with col:
            st.metric(label=f"📍 {top_branches[i]}", value=f"{bp_vols[i]} Leads", delta=f"{bp_pcts[i]} Share", delta_color="off")
    
    st.divider()

    # --- SECTION 1: CONVERSION, AGING SLA & FLIGHT RISK ---
    st.markdown('<div class="section-header"><h2>📊 1. Conversion, Aging & Immediate Flight Risk</h2></div>', unsafe_allow_html=True)
    
    col_c1, col_c2, col_c3 = st.columns(3)
    
    # Shared Y-Axis order (Top to Bottom)
    shared_y_branches = ['Delhi', 'Mumbai', 'Bangalore', 'Pune', 'Kolkata', 'Hyderabad', 'Chennai']
    
    # 1. CONVERSION CHART
    with col_c1:
        st.markdown("<h4 style='text-align: center; color: #475569;'>BP ➔ Login Rate<br><span style='font-size:14px; font-weight:normal;'>(Nat. Avg: 77.0%)</span></h4>", unsafe_allow_html=True)
        
        conv_rates = [60.6, 74.1, 79.0, 77.9, 83.8, 78.5, 74.0]
        nat_avg = 77.0
        
        # Color logic: Red if below average, Light grey/blue if above
        conv_colors = ["#9f1239" if val < nat_avg else "#cbd5e1" for val in conv_rates]
        
        fig_conv = go.Figure(go.Bar(
            y=shared_y_branches, x=conv_rates, orientation='h', marker_color=conv_colors,
            text=[f"{v}%" for v in conv_rates], textposition="inside", insidetextanchor="middle", 
            textfont=dict(color=["white" if c == "#9f1239" else "#0f172a" for c in conv_colors], weight="bold")
        ))
        
        fig_conv.add_vline(x=nat_avg, line_dash="dash", line_color="#475569", line_width=2)
        fig_conv.update_layout(
            height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569"))
        )
        st.plotly_chart(fig_conv, use_container_width=True)

    # 2. AGING / TAT CHART
    with col_c2:
        st.markdown("<h4 style='text-align: center; color: #475569;'>BP ➔ Login Stage TAT<br><span style='font-size:14px; font-weight:normal;'>(Target SLA: 3 Days)</span></h4>", unsafe_allow_html=True)
        
        tat_days = [5.6, 4.1, 2.8, 3.2, 4.4, 2.3, 1.9]
        target_tat = 3.0
        
        # Color logic: Red if SLA breached (> 3), Light grey/blue if healthy (< 3)
        tat_colors = ["#9f1239" if val > target_tat else "#cbd5e1" for val in tat_days]
        
        fig_tat = go.Figure(go.Bar(
            y=shared_y_branches, x=tat_days, orientation='h', marker_color=tat_colors,
            text=[f"{v} days" for v in tat_days], textposition="inside", insidetextanchor="middle", 
            textfont=dict(color=["white" if c == "#9f1239" else "#0f172a" for c in tat_colors], weight="bold")
        ))
        
        fig_tat.add_vline(x=target_tat, line_dash="dash", line_color="#475569", line_width=2)
        fig_tat.update_layout(
            height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed")
        )
        st.plotly_chart(fig_tat, use_container_width=True)

    # 3. PAID PF COMPETITOR (FLIGHT RISK)
    with col_c3:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Active BP vs. Paid to Competitor<br><span style='font-size:14px; font-weight:normal;'><span style='color:#cbd5e1'>■</span> True Active BP &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#f97316'>■</span> Paid Competitor</span></h4>", unsafe_allow_html=True)
        
        # Data aligned to the shared Y-axis (Delhi at top, Chennai at bottom)
        true_active_bp = [16, 22, 60, 32, 35, 45, 30] 
        paid_comp_bp = [3, 5, 20, 6, 8, 10, 8]
        paid_pcts = [f"({int((p/(a+p))*100)}%)" for a, p in zip(true_active_bp, paid_comp_bp)]

        fig_flight = go.Figure()
        
        # Grey: True Workable BP Leads
        fig_flight.add_trace(go.Bar(
            name="True Active BP", y=shared_y_branches, x=true_active_bp, orientation='h', marker_color="#e2e8f0",
            text=true_active_bp, textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")
        ))
        
        # Orange: Competitor Flight Risk
        fig_flight.add_trace(go.Bar(
            name="Paid Competitor", y=shared_y_branches, x=paid_comp_bp, orientation='h', marker_color="#f97316",
            text=[f"{v} {pct}" for v, pct in zip(paid_comp_bp, paid_pcts)], 
            textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")
        ))
        
        fig_flight.update_layout(
            barmode="stack", height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"),
            showlegend=False
        )
        st.plotly_chart(fig_flight, use_container_width=True)

    st.divider()

    # --- (Still Part of Section 1) TRUE WORKABLE BP LEADS BREAKDOWN ---
    st.subheader("🔎 True Workable BP Leads Breakdown")
    st.markdown("Taking the **True Active BP** leads from above and analyzing their **Aging (Left)** alongside their **Competitor Flight Risk Status (Right)**.")

    col_w1, col_w2 = st.columns(2)
    
    with col_w1:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Active Leads Aging</h4>", unsafe_allow_html=True)
        
        bp_under_7 = [10, 12, 35, 18, 20, 25, 18]
        bp_over_7 = [6, 10, 25, 14, 15, 20, 12]

        fig_bp_aging = go.Figure()

        # Healthy (< 7 Days)
        fig_bp_aging.add_trace(go.Bar(
            name="< 7 Days", y=shared_y_branches, x=bp_under_7, orientation='h', marker_color="#60a5fa",
            text=[f"{v}" if v > 0 else "" for v in bp_under_7], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")
        ))
        
        # Aging (> 7 Days)
        fig_bp_aging.add_trace(go.Bar(
            name="> 7 Days", y=shared_y_branches, x=bp_over_7, orientation='h', marker_color="#ef4444",
            text=[f"{v}" if v > 0 else "" for v in bp_over_7], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")
        ))

        fig_bp_aging.update_layout(
            barmode="stack", height=380, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569"))
        )
        st.plotly_chart(fig_bp_aging, use_container_width=True)

    with col_w2:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Competitor Pipeline Spread</h4>", unsafe_allow_html=True)
        
        bp_exclusive = [8, 10, 25, 12, 15, 20, 15] 
        bp_comp_login = [5, 7, 15, 10, 10, 12, 10]
        bp_comp_sanc = [3, 5, 20, 10, 10, 13, 5]

        fig_bp_work = go.Figure()

        fig_bp_work.add_trace(go.Bar(
            name="Exclusive (Safe)", y=shared_y_branches, x=bp_exclusive, orientation='h', marker_color="#a7f3d0",
            text=[f"{v}" if v > 0 else "" for v in bp_exclusive], textposition="inside", insidetextanchor="middle", textfont=dict(color="#0f172a", weight="bold")
        ))
        fig_bp_work.add_trace(go.Bar(
            name="⚠️ In Comp Login", y=shared_y_branches, x=bp_comp_login, orientation='h', marker_color="#fef08a",
            text=[f"{v}" if v > 0 else "" for v in bp_comp_login], textposition="inside", insidetextanchor="middle", textfont=dict(color="#854d0e", weight="bold")
        ))
        fig_bp_work.add_trace(go.Bar(
            name="🚨 In Comp Sanction", y=shared_y_branches, x=bp_comp_sanc, orientation='h', marker_color="#fda4af",
            text=[f"{v}" if v > 0 else "" for v in bp_comp_sanc], textposition="inside", insidetextanchor="middle", textfont=dict(color="#881337", weight="bold")
        ))

        fig_bp_work.update_layout(
            barmode="stack", height=380, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed") 
        )
        st.plotly_chart(fig_bp_work, use_container_width=True)

    st.divider()

    # ==========================================
    # --- SECTION 2: INPUT AND ADAPTABILITY ---
    # ==========================================
    st.markdown('<div class="section-header"><h2>⚙️ 2. Input and Adaptability (BP Stage)</h2></div>', unsafe_allow_html=True)
    st.markdown("Monitoring the status of raised **BP-related** queries and the average aging (in days) of **unresolved** tickets.")

    branches_query = ['📍 Bangalore', '📍 Hyderabad', '📍 Mumbai', '📍 Delhi', '📍 Pune', '📍 Chennai']
    resolved = [95, 60, 45, 20, 25, 22]
    unresolved = [25, 25, 15, 25, 5, 3]
    avg_aging_unresolved = [1.2, 2.5, 1.8, 5.4, 0.5, 0.8] 
    
    target_sla_days = 2.0 

    c_q1, c_q2 = st.columns(2)

    with c_q1:
        st.subheader("BP Query Status Volume")
        fig_bp_q_vol = go.Figure()
        
        fig_bp_q_vol.add_trace(go.Bar(
            x=branches_query, y=resolved, name='Resolved', marker_color='#3b82f6',
            text=resolved, textposition='inside', insidetextfont=dict(color="white", weight="bold")
        ))
        fig_bp_q_vol.add_trace(go.Bar(
            x=branches_query, y=unresolved, name='Unresolved', marker_color='#f59e0b',
            text=unresolved, textposition='outside', textfont=dict(color="#b45309", weight="bold")
        ))
        
        fig_bp_q_vol.update_layout(
            barmode='stack', height=350, margin=dict(t=20, b=20, l=20, r=20),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
            yaxis=dict(showgrid=True, gridcolor='#e2e8f0', title="Total Queries", range=[0, 135])
        )
        st.plotly_chart(fig_bp_q_vol, use_container_width=True, key="tab5_q_vol")

    with c_q2:
        st.subheader("Avg. Aging of Unresolved BP Queries")
        
        aging_colors = ["#9f1239" if age > target_sla_days else "#94a3b8" for age in avg_aging_unresolved]
        
        fig_bp_q_age = go.Figure()
        fig_bp_q_age.add_trace(go.Bar(
            x=branches_query, y=avg_aging_unresolved, marker_color=aging_colors,
            text=[f"{age} days" for age in avg_aging_unresolved], 
            textposition='outside', textfont=dict(weight="bold")
        ))
        
        fig_bp_q_age.add_hline(
            y=target_sla_days, line_dash="dash", line_color="#ef4444", line_width=2,
            annotation_text=f"Target SLA ({target_sla_days} Days)", annotation_position="top right", 
            annotation_font_color="#ef4444"
        )

        fig_bp_q_age.update_layout(
            height=350, margin=dict(t=20, b=20, l=20, r=20),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False,
            yaxis=dict(showgrid=True, gridcolor='#e2e8f0', title="Days Unresolved", range=[0, 6.5])
        )
        st.plotly_chart(fig_bp_q_age, use_container_width=True, key="tab5_q_age")

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📞 System Dispositions & Last Touch Base (Total Shared Leads)")
    st.markdown("Measuring RM system adoption (Logged vs. Unknown) and the recency of the last touch base for all logged leads.")

    col_disp, col_ltb = st.columns(2)

    with col_disp:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Form Dispositions vs. Unknown</h4>", unsafe_allow_html=True)
        
        branches_disp = ['📍 Chennai', '📍 Hyderabad', '📍 Bangalore', '📍 Mumbai', '📍 Delhi', '📦 Others']
        unknown_leads = [150, 329, 686, 200, 101, 113]
        logged_leads = [278, 385, 456, 85, 42, 30]
        logged_pcts = [65.0, 53.9, 39.9, 29.8, 29.4, 21.0]

        fig_disp = go.Figure()
        
        fig_disp.add_trace(go.Bar(
            name="Unknown / Offline", y=branches_disp, x=unknown_leads, orientation='h', marker_color="#e2e8f0",
            text=[f"Unknown: {v}" for v in unknown_leads], textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")
        ))
        
        fig_disp.add_trace(go.Bar(
            name="Logged via Form", y=branches_disp, x=logged_leads, orientation='h', marker_color="#10b981",
            text=[f"Logged: {l} ({p}%)" for l, p in zip(logged_leads, logged_pcts)], 
            textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")
        ))

        fig_disp.update_layout(
            barmode="stack", height=380, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569"))
        )
        st.plotly_chart(fig_disp, use_container_width=True)

    with col_ltb:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Last Touch Base (LTB) Aging</h4>", unsafe_allow_html=True)
        
        ltb_0_3 = [150, 185, 150, 30, 15, 10]
        ltb_4_7 = [80, 120, 150, 35, 15, 10]
        ltb_over_7 = [48, 80, 156, 20, 12, 10]

        fig_ltb = go.Figure()
        
        fig_ltb.add_trace(go.Bar(
            name="0-3 Days", y=branches_disp, x=ltb_0_3, orientation='h', marker_color="#34d399",
            text=[f"{v}" if v > 0 else "" for v in ltb_0_3], textposition="inside", insidetextanchor="middle", textfont=dict(color="#064e3b", weight="bold")
        ))
        
        fig_ltb.add_trace(go.Bar(
            name="4-7 Days", y=branches_disp, x=ltb_4_7, orientation='h', marker_color="#fbbf24",
            text=[f"{v}" if v > 0 else "" for v in ltb_4_7], textposition="inside", insidetextanchor="middle", textfont=dict(color="#78350f", weight="bold")
        ))
        
        fig_ltb.add_trace(go.Bar(
            name="> 7 Days", y=branches_disp, x=ltb_over_7, orientation='h', marker_color="#ef4444",
            text=[f"{v}" if v > 0 else "" for v in ltb_over_7], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")
        ))

        fig_ltb.update_layout(
            barmode="stack", height=380, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed") 
        )
        st.plotly_chart(fig_ltb, use_container_width=True)
        st.divider()

    # ==========================================
    # --- SECTION 3: BP STAGE LOST ANALYSIS ---
    # ==========================================
    st.markdown('<div class="section-header"><h2>🚨 3. BP Stage Lost Analysis</h2></div>', unsafe_allow_html=True)
    st.markdown("Analyzing the volume of leads marked as **Lost from the BP Stage**, and tracking their subsequent movement into competitor pipelines.")

    col_l1, col_l2 = st.columns(2)

    with col_l1:
        # ADDED FIX: An invisible second line (<br><span style='visibility:hidden;'>...</span>) forces this header to be the exact same height as the right header!
        st.markdown("<h4 style='text-align: center; color: #475569;'>BP Leakage Rate (% of Shared)<br><span style='font-size:13px; visibility:hidden;'>Invisible Spacer For Alignment</span></h4>", unsafe_allow_html=True)
        
        bp_leakage_pcts = [33.6, 19.2, 14.4, 12.8, 13.4, 14.1, 10.2]
        
        leakage_colors = ["#9f1239" if p > 20 else ("#ef4444" if p > 13 else "#fca5a5") for p in bp_leakage_pcts]

        fig_bp_leakage = go.Figure(go.Bar(
            y=shared_y_branches, x=bp_leakage_pcts, orientation='h', marker_color=leakage_colors,
            text=[f"{p}%" for p in bp_leakage_pcts], textposition="inside", insidetextanchor="middle", 
            textfont=dict(color=["white" if c in ["#9f1239", "#ef4444"] else "#0f172a" for c in leakage_colors], weight="bold")
        ))

        fig_bp_leakage.update_layout(
            height=350, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569"))
        )
        st.plotly_chart(fig_bp_leakage, use_container_width=True)

    with col_l2:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Competitor Pipeline Spread (Lost Leads)<br><span style='font-size:13px; font-weight:normal;'><span style='color:#e2e8f0'>■</span> True Dead &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#fdba74'>■</span> Comp Login &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#f97316'>■</span> Comp Sanction &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#9f1239'>■</span> Comp PF Paid</span></h4>", unsafe_allow_html=True)
        
        true_dead = [5, 10, 30, 5, 10, 15, 5]
        comp_log = [10, 15, 40, 10, 10, 15, 5]
        comp_san = [15, 10, 30, 5, 5, 10, 5]
        comp_pf = [15, 15, 50, 10, 10, 20, 5]

        # Calculate total lost volume per branch and the Lost Potential % (Competitor Volume / Total Lost Volume)
        bp_lost_totals = [t + l + s + p for t, l, s, p in zip(true_dead, comp_log, comp_san, comp_pf)]
        bp_potential_loss_pcts = [f"{((tot - td) / tot) * 100:.1f}%" for tot, td in zip(bp_lost_totals, true_dead)]

        fig_bp_lost_spread = go.Figure()

        fig_bp_lost_spread.add_trace(go.Bar(
            name="True Dead", y=shared_y_branches, x=true_dead, orientation='h', marker_color="#e2e8f0",
            text=[f"{v}" if v > 0 else "" for v in true_dead], textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")
        ))
        fig_bp_lost_spread.add_trace(go.Bar(
            name="Comp Login", y=shared_y_branches, x=comp_log, orientation='h', marker_color="#fdba74",
            text=[f"{v}" if v > 0 else "" for v in comp_log], textposition="inside", insidetextanchor="middle", textfont=dict(color="#9a3412", weight="bold")
        ))
        fig_bp_lost_spread.add_trace(go.Bar(
            name="Comp Sanction", y=shared_y_branches, x=comp_san, orientation='h', marker_color="#f97316",
            text=[f"{v}" if v > 0 else "" for v in comp_san], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")
        ))
        fig_bp_lost_spread.add_trace(go.Bar(
            name="Comp PF Paid", y=shared_y_branches, x=comp_pf, orientation='h', marker_color="#9f1239",
            text=[f"{v}" if v > 0 else "" for v in comp_pf], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")
        ))

        # Dynamically append the Lost Potential annotations to the end of each bar
        for i, branch in enumerate(shared_y_branches):
            fig_bp_lost_spread.add_annotation(
                x=bp_lost_totals[i], y=branch,
                text=f"<span style='color:#64748b; font-size:11px; font-weight:normal;'>Lost Potential</span><br><b style='font-size:16px; color:#9f1239;'>⚠️ {bp_potential_loss_pcts[i]}</b>",
                showarrow=False, xanchor="left", xshift=12, align="left"
            )

        fig_bp_lost_spread.update_layout(
            # Increased right margin (r=90) and locked x-axis range to prevent the new annotations from clipping
            barmode="stack", height=350, margin=dict(t=20, b=20, l=10, r=90), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False, range=[0, 190]), yaxis=dict(showticklabels=False, autorange="reversed"), 
            showlegend=False 
        )
        st.plotly_chart(fig_bp_lost_spread, use_container_width=True)

# ==========================================
# TAB 6: LOGIN TO SANCTION DEEP DIVE
# ==========================================
with tab_log_san:
    # --- TOP CARDS: VOLUME DISTRIBUTION ---
    st.markdown('<div class="section-header"><h2>🗂️ Login Stage Lead Distribution</h2></div>', unsafe_allow_html=True)
    
    top_branches = ["Bangalore", "Hyderabad", "Chennai", "Mumbai", "Delhi", "Others"]
    log_vols = [850, 500, 300, 200, 90, 100]
    log_pcts = ["41.6%", "24.5%", "14.7%", "9.8%", "4.4%", "4.9%"]
    
    card_cols = st.columns(6)
    for i, col in enumerate(card_cols):
        with col:
            st.metric(label=f"📍 {top_branches[i]}", value=f"{log_vols[i]} Logins", delta=f"{log_pcts[i]} Share", delta_color="off")
    
    st.divider()

    # --- SECTION 1: CONVERSION, AGING SLA & FLIGHT RISK ---
    st.markdown('<div class="section-header"><h2>📊 1. Conversion, Aging & Immediate Flight Risk</h2></div>', unsafe_allow_html=True)
    
    col_c1, col_c2, col_c3 = st.columns(3)
    shared_y_branches = ['Delhi', 'Mumbai', 'Bangalore', 'Pune', 'Kolkata', 'Hyderabad', 'Chennai']
    
    with col_c1:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Login ➔ Sanction Rate<br><span style='font-size:14px; font-weight:normal;'>(Nat. Avg: 47.8%)</span></h4>", unsafe_allow_html=True)
        
        conv_rates = [61.4, 46.2, 45.8, 49.4, 51.9, 53.5, 49.4]
        nat_avg = 47.8
        conv_colors = ["#9f1239" if val < nat_avg else "#cbd5e1" for val in conv_rates]
        
        fig_conv = go.Figure(go.Bar(
            y=shared_y_branches, x=conv_rates, orientation='h', marker_color=conv_colors,
            text=[f"{v}%" for v in conv_rates], textposition="inside", insidetextanchor="middle", 
            textfont=dict(color=["white" if c == "#9f1239" else "#0f172a" for c in conv_colors], weight="bold")
        ))
        
        fig_conv.add_vline(x=nat_avg, line_dash="dash", line_color="#475569", line_width=2)
        fig_conv.update_layout(
            height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569"))
        )
        st.plotly_chart(fig_conv, use_container_width=True)

    with col_c2:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Login ➔ Sanction TAT<br><span style='font-size:14px; font-weight:normal;'>(Target SLA: 7 Days)</span></h4>", unsafe_allow_html=True)
        
        tat_days = [8.1, 11.4, 12.8, 6.2, 9.5, 8.8, 5.4]
        target_tat = 7.0
        tat_colors = ["#9f1239" if val > target_tat else "#cbd5e1" for val in tat_days]
        
        fig_tat = go.Figure(go.Bar(
            y=shared_y_branches, x=tat_days, orientation='h', marker_color=tat_colors,
            text=[f"{v} days" for v in tat_days], textposition="inside", insidetextanchor="middle", 
            textfont=dict(color=["white" if c == "#9f1239" else "#0f172a" for c in tat_colors], weight="bold")
        ))
        
        fig_tat.add_vline(x=target_tat, line_dash="dash", line_color="#475569", line_width=2)
        fig_tat.update_layout(
            height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed") 
        )
        st.plotly_chart(fig_tat, use_container_width=True)

    with col_c3:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Active Login vs. Paid to Competitor<br><span style='font-size:14px; font-weight:normal;'><span style='color:#cbd5e1'>■</span> True Active Login &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#f97316'>■</span> Paid Competitor</span></h4>", unsafe_allow_html=True)
        
        true_active_log = [8, 15, 50, 20, 25, 35, 20] 
        paid_comp_log = [1, 3, 13, 4, 5, 7, 5]
        paid_pcts = [f"({int((p/(a+p))*100)}%)" for a, p in zip(true_active_log, paid_comp_log)]

        fig_flight = go.Figure()
        fig_flight.add_trace(go.Bar(
            name="True Active Login", y=shared_y_branches, x=true_active_log, orientation='h', marker_color="#e2e8f0",
            text=true_active_log, textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")
        ))
        fig_flight.add_trace(go.Bar(
            name="Paid Competitor", y=shared_y_branches, x=paid_comp_log, orientation='h', marker_color="#f97316",
            text=[f"{v} {pct}" for v, pct in zip(paid_comp_log, paid_pcts)], 
            textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")
        ))
        fig_flight.update_layout(
            barmode="stack", height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"),
            showlegend=False 
        )
        st.plotly_chart(fig_flight, use_container_width=True)

    st.divider()

    # --- TRUE WORKABLE LOGIN LEADS BREAKDOWN ---
    st.subheader("🔎 True Workable Login Leads Breakdown")
    st.markdown("Taking the **True Active Login** leads from above and analyzing their **Aging (Left)** alongside their **Competitor Flight Risk Status (Right)**.")

    col_w1, col_w2 = st.columns(2)
    
    with col_w1:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Active Leads Aging</h4>", unsafe_allow_html=True)
        
        log_under_7 = [5, 10, 30, 12, 15, 20, 12]
        log_over_7 = [3, 5, 20, 8, 10, 15, 8]

        fig_log_aging = go.Figure()
        fig_log_aging.add_trace(go.Bar(
            name="< 7 Days", y=shared_y_branches, x=log_under_7, orientation='h', marker_color="#60a5fa",
            text=[f"{v}" if v > 0 else "" for v in log_under_7], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")
        ))
        fig_log_aging.add_trace(go.Bar(
            name="> 7 Days", y=shared_y_branches, x=log_over_7, orientation='h', marker_color="#ef4444",
            text=[f"{v}" if v > 0 else "" for v in log_over_7], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")
        ))

        fig_log_aging.update_layout(
            barmode="stack", height=380, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569"))
        )
        st.plotly_chart(fig_log_aging, use_container_width=True)

    with col_w2:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Competitor Pipeline Spread</h4>", unsafe_allow_html=True)
        
        # In Login stage, they can only be Exclusive or Comp Sanction
        log_exclusive = [6, 10, 35, 15, 18, 25, 14] 
        log_comp_sanc = [2, 5, 15, 5, 7, 10, 6]

        fig_log_work = go.Figure()
        fig_log_work.add_trace(go.Bar(
            name="Exclusive (Safe)", y=shared_y_branches, x=log_exclusive, orientation='h', marker_color="#a7f3d0",
            text=[f"{v}" if v > 0 else "" for v in log_exclusive], textposition="inside", insidetextanchor="middle", textfont=dict(color="#0f172a", weight="bold")
        ))
        fig_log_work.add_trace(go.Bar(
            name="🚨 In Comp Sanction", y=shared_y_branches, x=log_comp_sanc, orientation='h', marker_color="#fda4af",
            text=[f"{v}" if v > 0 else "" for v in log_comp_sanc], textposition="inside", insidetextanchor="middle", textfont=dict(color="#881337", weight="bold")
        ))

        fig_log_work.update_layout(
            barmode="stack", height=380, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed") 
        )
        st.plotly_chart(fig_log_work, use_container_width=True)

    st.divider()

    # ==========================================
    # --- SECTION 2: INPUT AND ADAPTABILITY ---
    # ==========================================
    st.markdown('<div class="section-header"><h2>⚙️ 2. Input and Adaptability (Login Stage)</h2></div>', unsafe_allow_html=True)
    
    branches_query = ['📍 Bangalore', '📍 Hyderabad', '📍 Mumbai', '📍 Delhi', '📍 Pune', '📍 Chennai']
    resolved = [140, 95, 65, 30, 45, 35]
    unresolved = [35, 40, 20, 30, 8, 5]
    avg_aging_unresolved = [2.2, 3.8, 2.8, 6.4, 1.5, 1.8] 
    target_sla_days = 3.0 

    c_q1, c_q2 = st.columns(2)

    with c_q1:
        st.subheader("Login Query Status Volume")
        fig_log_q_vol = go.Figure()
        fig_log_q_vol.add_trace(go.Bar(
            x=branches_query, y=resolved, name='Resolved', marker_color='#3b82f6',
            text=resolved, textposition='inside', insidetextfont=dict(color="white", weight="bold")
        ))
        fig_log_q_vol.add_trace(go.Bar(
            x=branches_query, y=unresolved, name='Unresolved', marker_color='#f59e0b',
            text=unresolved, textposition='outside', textfont=dict(color="#b45309", weight="bold")
        ))
        fig_log_q_vol.update_layout(
            barmode='stack', height=350, margin=dict(t=20, b=20, l=20, r=20),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
            yaxis=dict(showgrid=True, gridcolor='#e2e8f0', title="Total Queries")
        )
        st.plotly_chart(fig_log_q_vol, use_container_width=True, key="tab6_q_vol")

    with c_q2:
        st.subheader("Avg. Aging of Unresolved Login Queries")
        aging_colors = ["#9f1239" if age > target_sla_days else "#94a3b8" for age in avg_aging_unresolved]
        
        fig_log_q_age = go.Figure()
        fig_log_q_age.add_trace(go.Bar(
            x=branches_query, y=avg_aging_unresolved, marker_color=aging_colors,
            text=[f"{age} days" for age in avg_aging_unresolved], 
            textposition='outside', textfont=dict(weight="bold")
        ))
        fig_log_q_age.add_hline(
            y=target_sla_days, line_dash="dash", line_color="#ef4444", line_width=2,
            annotation_text=f"Target SLA ({target_sla_days} Days)", annotation_position="top right", 
            annotation_font_color="#ef4444"
        )
        fig_log_q_age.update_layout(
            height=350, margin=dict(t=20, b=20, l=20, r=20),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False,
            yaxis=dict(showgrid=True, gridcolor='#e2e8f0', title="Days Unresolved")
        )
        st.plotly_chart(fig_log_q_age, use_container_width=True, key="tab6_q_age")

    st.divider()

    # ==========================================
    # --- SECTION 3: LOGIN STAGE LOST ANALYSIS ---
    # ==========================================
    st.markdown('<div class="section-header"><h2>🚨 3. Login Stage Lost Analysis</h2></div>', unsafe_allow_html=True)
    st.markdown("Analyzing the volume of leads marked as **Lost from the Login Stage**, and tracking their subsequent movement into competitor pipelines.")

    col_l1, col_l2 = st.columns(2)

    with col_l1:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Login Leakage Rate (% of Logins)<br><span style='font-size:13px; visibility:hidden;'>Invisible Spacer</span></h4>", unsafe_allow_html=True)
        
        log_leakage_pcts = [16.9, 24.2, 34.5, 17.0, 32.1, 37.1, 25.3]
        leakage_colors = ["#9f1239" if p > 30 else ("#ef4444" if p > 20 else "#fca5a5") for p in log_leakage_pcts]

        fig_log_leakage = go.Figure(go.Bar(
            y=shared_y_branches, x=log_leakage_pcts, orientation='h', marker_color=leakage_colors,
            text=[f"{p}%" for p in log_leakage_pcts], textposition="inside", insidetextanchor="middle", 
            textfont=dict(color=["white" if c in ["#9f1239", "#ef4444"] else "#0f172a" for c in leakage_colors], weight="bold")
        ))
        fig_log_leakage.update_layout(
            height=350, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569"))
        )
        st.plotly_chart(fig_log_leakage, use_container_width=True)

    with col_l2:
        # Adjusted HTML legend to exclude Comp Login
        st.markdown("<h4 style='text-align: center; color: #475569;'>Competitor Pipeline Spread (Lost Leads)<br><span style='font-size:13px; font-weight:normal;'><span style='color:#e2e8f0'>■</span> True Dead &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#f97316'>■</span> Comp Sanction &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#9f1239'>■</span> Comp PF Paid</span></h4>", unsafe_allow_html=True)
        
        true_dead = [2, 15, 45, 5, 15, 25, 10]
        comp_san = [8, 12, 35, 10, 10, 20, 8]
        comp_pf = [5, 18, 55, 15, 12, 30, 12]

        log_lost_totals = [t + s + p for t, s, p in zip(true_dead, comp_san, comp_pf)]
        log_potential_loss_pcts = [f"{((tot - td) / tot) * 100:.1f}%" for tot, td in zip(log_lost_totals, true_dead)]

        fig_log_lost_spread = go.Figure()
        fig_log_lost_spread.add_trace(go.Bar(
            name="True Dead", y=shared_y_branches, x=true_dead, orientation='h', marker_color="#e2e8f0",
            text=[f"{v}" if v > 0 else "" for v in true_dead], textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")
        ))
        fig_log_lost_spread.add_trace(go.Bar(
            name="Comp Sanction", y=shared_y_branches, x=comp_san, orientation='h', marker_color="#f97316",
            text=[f"{v}" if v > 0 else "" for v in comp_san], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")
        ))
        fig_log_lost_spread.add_trace(go.Bar(
            name="Comp PF Paid", y=shared_y_branches, x=comp_pf, orientation='h', marker_color="#9f1239",
            text=[f"{v}" if v > 0 else "" for v in comp_pf], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")
        ))

        for i, branch in enumerate(shared_y_branches):
            fig_log_lost_spread.add_annotation(
                x=log_lost_totals[i], y=branch,
                text=f"<span style='color:#64748b; font-size:11px; font-weight:normal;'>Lost Potential</span><br><b style='font-size:16px; color:#9f1239;'>⚠️ {log_potential_loss_pcts[i]}</b>",
                showarrow=False, xanchor="left", xshift=12, align="left"
            )

        fig_log_lost_spread.update_layout(
            barmode="stack", height=350, margin=dict(t=20, b=20, l=10, r=90), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False, range=[0, 150]), yaxis=dict(showticklabels=False, autorange="reversed"), 
            showlegend=False 
        )
        st.plotly_chart(fig_log_lost_spread, use_container_width=True)

# ==========================================
# TAB 7: SANCTION TO PF DEEP DIVE
# ==========================================
with tab_san_pf:
    # --- TOP CARDS: VOLUME DISTRIBUTION ---
    st.markdown('<div class="section-header"><h2>🗂️ Sanction Stage Lead Distribution</h2></div>', unsafe_allow_html=True)
    
    top_branches = ["Bangalore", "Hyderabad", "Chennai", "Mumbai", "Delhi", "Others"]
    san_vols = [420, 250, 150, 90, 40, 45]
    san_pcts = ["42.2%", "25.1%", "15.1%", "9.0%", "4.0%", "4.5%"]
    
    card_cols = st.columns(6)
    for i, col in enumerate(card_cols):
        with col:
            st.metric(label=f"📍 {top_branches[i]}", value=f"{san_vols[i]} Sanctions", delta=f"{san_pcts[i]} Share", delta_color="off")
    
    st.divider()

    # --- SECTION 1: CONVERSION, AGING SLA & FLIGHT RISK ---
    st.markdown('<div class="section-header"><h2>📊 1. Conversion, Aging & Immediate Flight Risk</h2></div>', unsafe_allow_html=True)
    
    col_c1, col_c2, col_c3 = st.columns(3)
    shared_y_branches = ['Delhi', 'Mumbai', 'Bangalore', 'Pune', 'Kolkata', 'Hyderabad', 'Chennai']
    
    with col_c1:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Sanction ➔ PF Rate<br><span style='font-size:14px; font-weight:normal;'>(Nat. Avg: 49.8%)</span></h4>", unsafe_allow_html=True)
        
        conv_rates = [41.2, 45.1, 49.2, 50.6, 46.4, 52.7, 61.7]
        nat_avg = 49.8
        conv_colors = ["#9f1239" if val < nat_avg else "#cbd5e1" for val in conv_rates]
        
        fig_conv = go.Figure(go.Bar(
            y=shared_y_branches, x=conv_rates, orientation='h', marker_color=conv_colors,
            text=[f"{v}%" for v in conv_rates], textposition="inside", insidetextanchor="middle", 
            textfont=dict(color=["white" if c == "#9f1239" else "#0f172a" for c in conv_colors], weight="bold")
        ))
        
        fig_conv.add_vline(x=nat_avg, line_dash="dash", line_color="#475569", line_width=2)
        fig_conv.update_layout(
            height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569"))
        )
        st.plotly_chart(fig_conv, use_container_width=True)

    with col_c2:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Sanction ➔ PF TAT<br><span style='font-size:14px; font-weight:normal;'>(Target SLA: 5 Days)</span></h4>", unsafe_allow_html=True)
        
        tat_days = [3.9, 6.1, 7.4, 4.2, 4.8, 9.2, 3.2]
        target_tat = 5.0
        tat_colors = ["#9f1239" if val > target_tat else "#cbd5e1" for val in tat_days]
        
        fig_tat = go.Figure(go.Bar(
            y=shared_y_branches, x=tat_days, orientation='h', marker_color=tat_colors,
            text=[f"{v} days" for v in tat_days], textposition="inside", insidetextanchor="middle", 
            textfont=dict(color=["white" if c == "#9f1239" else "#0f172a" for c in tat_colors], weight="bold")
        ))
        
        fig_tat.add_vline(x=target_tat, line_dash="dash", line_color="#475569", line_width=2)
        fig_tat.update_layout(
            height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed") 
        )
        st.plotly_chart(fig_tat, use_container_width=True)

    with col_c3:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Active Sanction vs. Paid to Competitor<br><span style='font-size:14px; font-weight:normal;'><span style='color:#cbd5e1'>■</span> True Active Sanction &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#f97316'>■</span> Paid Competitor</span></h4>", unsafe_allow_html=True)
        
        true_active_san = [5, 8, 25, 10, 12, 20, 10] 
        paid_comp_san = [1, 4, 15, 2, 3, 7, 3]
        paid_pcts = [f"({int((p/(a+p))*100)}%)" for a, p in zip(true_active_san, paid_comp_san)]

        fig_flight = go.Figure()
        fig_flight.add_trace(go.Bar(
            name="True Active Sanction", y=shared_y_branches, x=true_active_san, orientation='h', marker_color="#e2e8f0",
            text=true_active_san, textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")
        ))
        fig_flight.add_trace(go.Bar(
            name="Paid Competitor", y=shared_y_branches, x=paid_comp_san, orientation='h', marker_color="#f97316",
            text=[f"{v} {pct}" for v, pct in zip(paid_comp_san, paid_pcts)], 
            textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")
        ))
        fig_flight.update_layout(
            barmode="stack", height=350, margin=dict(t=10, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"),
            showlegend=False 
        )
        st.plotly_chart(fig_flight, use_container_width=True)

    st.divider()

    # --- TRUE WORKABLE SANCTION LEADS BREAKDOWN ---
    st.subheader("🔎 True Workable Sanction Leads Breakdown")
    st.markdown("Taking the **True Active Sanction** leads from above and analyzing their **Aging (Left)** alongside their **Competitor Flight Risk Status (Right)**.")

    col_w1, col_w2 = st.columns(2)
    
    with col_w1:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Active Leads Aging</h4>", unsafe_allow_html=True)
        
        san_under_7 = [3, 5, 15, 6, 8, 12, 7]
        san_over_7 = [2, 3, 10, 4, 4, 8, 3]

        fig_san_aging = go.Figure()
        fig_san_aging.add_trace(go.Bar(
            name="< 7 Days", y=shared_y_branches, x=san_under_7, orientation='h', marker_color="#60a5fa",
            text=[f"{v}" if v > 0 else "" for v in san_under_7], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")
        ))
        fig_san_aging.add_trace(go.Bar(
            name="> 7 Days", y=shared_y_branches, x=san_over_7, orientation='h', marker_color="#ef4444",
            text=[f"{v}" if v > 0 else "" for v in san_over_7], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")
        ))

        fig_san_aging.update_layout(
            barmode="stack", height=380, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569"))
        )
        st.plotly_chart(fig_san_aging, use_container_width=True)

    with col_w2:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Competitor Pipeline Spread</h4>", unsafe_allow_html=True)
        
        # In Sanction stage, if active, they are either Exclusive or processing a Parallel Sanction elsewhere
        san_exclusive = [3, 5, 18, 7, 9, 14, 7] 
        san_comp_parallel = [2, 3, 7, 3, 3, 6, 3]

        fig_san_work = go.Figure()
        fig_san_work.add_trace(go.Bar(
            name="Exclusive (Safe)", y=shared_y_branches, x=san_exclusive, orientation='h', marker_color="#a7f3d0",
            text=[f"{v}" if v > 0 else "" for v in san_exclusive], textposition="inside", insidetextanchor="middle", textfont=dict(color="#0f172a", weight="bold")
        ))
        fig_san_work.add_trace(go.Bar(
            name="🚨 Parallel Comp Sanction", y=shared_y_branches, x=san_comp_parallel, orientation='h', marker_color="#fda4af",
            text=[f"{v}" if v > 0 else "" for v in san_comp_parallel], textposition="inside", insidetextanchor="middle", textfont=dict(color="#881337", weight="bold")
        ))

        fig_san_work.update_layout(
            barmode="stack", height=380, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed") 
        )
        st.plotly_chart(fig_san_work, use_container_width=True)

    st.divider()

    # ==========================================
    # --- SECTION 2: INPUT AND ADAPTABILITY ---
    # ==========================================
    st.markdown('<div class="section-header"><h2>⚙️ 2. Input and Adaptability (Sanction Stage)</h2></div>', unsafe_allow_html=True)
    
    branches_query = ['📍 Bangalore', '📍 Hyderabad', '📍 Mumbai', '📍 Delhi', '📍 Pune', '📍 Chennai']
    resolved = [80, 50, 40, 15, 20, 15]
    unresolved = [15, 12, 10, 8, 4, 2]
    avg_aging_unresolved = [1.5, 2.0, 1.2, 4.5, 0.8, 0.5] 
    target_sla_days = 2.0 

    c_q1, c_q2 = st.columns(2)

    with c_q1:
        st.subheader("Sanction Query Status Volume")
        fig_san_q_vol = go.Figure()
        fig_san_q_vol.add_trace(go.Bar(
            x=branches_query, y=resolved, name='Resolved', marker_color='#3b82f6',
            text=resolved, textposition='inside', insidetextfont=dict(color="white", weight="bold")
        ))
        fig_san_q_vol.add_trace(go.Bar(
            x=branches_query, y=unresolved, name='Unresolved', marker_color='#f59e0b',
            text=unresolved, textposition='outside', textfont=dict(color="#b45309", weight="bold")
        ))
        fig_san_q_vol.update_layout(
            barmode='stack', height=350, margin=dict(t=20, b=20, l=20, r=20),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
            yaxis=dict(showgrid=True, gridcolor='#e2e8f0', title="Total Queries")
        )
        st.plotly_chart(fig_san_q_vol, use_container_width=True, key="tab7_q_vol")

    with c_q2:
        st.subheader("Avg. Aging of Unresolved Sanction Queries")
        aging_colors = ["#9f1239" if age > target_sla_days else "#94a3b8" for age in avg_aging_unresolved]
        
        fig_san_q_age = go.Figure()
        fig_san_q_age.add_trace(go.Bar(
            x=branches_query, y=avg_aging_unresolved, marker_color=aging_colors,
            text=[f"{age} days" for age in avg_aging_unresolved], 
            textposition='outside', textfont=dict(weight="bold")
        ))
        fig_san_q_age.add_hline(
            y=target_sla_days, line_dash="dash", line_color="#ef4444", line_width=2,
            annotation_text=f"Target SLA ({target_sla_days} Days)", annotation_position="top right", 
            annotation_font_color="#ef4444"
        )
        fig_san_q_age.update_layout(
            height=350, margin=dict(t=20, b=20, l=20, r=20),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False,
            yaxis=dict(showgrid=True, gridcolor='#e2e8f0', title="Days Unresolved")
        )
        st.plotly_chart(fig_san_q_age, use_container_width=True, key="tab7_q_age")

    st.divider()

    # ==========================================
    # --- SECTION 3: SANCTION STAGE LOST ANALYSIS ---
    # ==========================================
    st.markdown('<div class="section-header"><h2>🚨 3. Sanction Stage Lost Analysis</h2></div>', unsafe_allow_html=True)
    st.markdown("Analyzing the volume of leads marked as **Lost from the Sanction Stage**. At this stage, files lost to competitors almost always indicate PF was paid elsewhere.")

    col_l1, col_l2 = st.columns(2)

    with col_l1:
        st.markdown("<h4 style='text-align: center; color: #475569;'>Sanction Leakage Rate (% of Sanctions)<br><span style='font-size:13px; visibility:hidden;'>Invisible Spacer</span></h4>", unsafe_allow_html=True)
        
        san_leakage_pcts = [0.0, 6.7, 5.3, 0.0, 0.9, 19.1, 0.0]
        leakage_colors = ["#9f1239" if p > 15 else ("#ef4444" if p > 5 else "#fca5a5") for p in san_leakage_pcts]

        fig_san_leakage = go.Figure(go.Bar(
            y=shared_y_branches, x=san_leakage_pcts, orientation='h', marker_color=leakage_colors,
            text=[f"{p}%" if p > 0 else "0%" for p in san_leakage_pcts], textposition="inside", insidetextanchor="middle", 
            textfont=dict(color=["white" if c in ["#9f1239", "#ef4444"] else "#0f172a" for c in leakage_colors], weight="bold")
        ))
        fig_san_leakage.update_layout(
            height=350, margin=dict(t=20, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(autorange="reversed", tickfont=dict(size=14, weight="bold", color="#475569"))
        )
        st.plotly_chart(fig_san_leakage, use_container_width=True)

    with col_l2:
        # Adjusted HTML legend to reflect binary Sanction loss outcome
        st.markdown("<h4 style='text-align: center; color: #475569;'>Competitor Pipeline Spread (Lost Leads)<br><span style='font-size:13px; font-weight:normal;'><span style='color:#e2e8f0'>■</span> True Dead &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#9f1239'>■</span> Comp PF Paid</span></h4>", unsafe_allow_html=True)
        
        true_dead = [0, 2, 8, 0, 1, 12, 0]
        comp_pf = [0, 5, 14, 0, 0, 35, 0]

        san_lost_totals = [t + p for t, p in zip(true_dead, comp_pf)]
        san_potential_loss_pcts = [f"{((tot - td) / tot) * 100:.1f}%" if tot > 0 else "0%" for tot, td in zip(san_lost_totals, true_dead)]

        fig_san_lost_spread = go.Figure()
        fig_san_lost_spread.add_trace(go.Bar(
            name="True Dead", y=shared_y_branches, x=true_dead, orientation='h', marker_color="#e2e8f0",
            text=[f"{v}" if v > 0 else "" for v in true_dead], textposition="inside", insidetextanchor="middle", textfont=dict(color="#475569", weight="bold")
        ))
        fig_san_lost_spread.add_trace(go.Bar(
            name="Comp PF Paid", y=shared_y_branches, x=comp_pf, orientation='h', marker_color="#9f1239",
            text=[f"{v}" if v > 0 else "" for v in comp_pf], textposition="inside", insidetextanchor="middle", textfont=dict(color="white", weight="bold")
        ))

        for i, branch in enumerate(shared_y_branches):
            if san_lost_totals[i] > 0:
                fig_san_lost_spread.add_annotation(
                    x=san_lost_totals[i], y=branch,
                    text=f"<span style='color:#64748b; font-size:11px; font-weight:normal;'>Lost Potential</span><br><b style='font-size:16px; color:#9f1239;'>⚠️ {san_potential_loss_pcts[i]}</b>",
                    showarrow=False, xanchor="left", xshift=12, align="left"
                )

        fig_san_lost_spread.update_layout(
            barmode="stack", height=350, margin=dict(t=20, b=20, l=10, r=90), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False, range=[0, 60]), yaxis=dict(showticklabels=False, autorange="reversed"), 
            showlegend=False 
        )
        st.plotly_chart(fig_san_lost_spread, use_container_width=True)
