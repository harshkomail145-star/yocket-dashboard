import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ==========================================
# 1. PAGE SETUP & CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Yocket Lending & Revenue Command Center",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for clean metrics and visual structure
st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ff9800;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MOCK DATA GENERATION ENGINE
# ==========================================
@st.cache_data
def generate_mock_data():
    np.random.seed(42)
    lenders = ["HDFC Credila", "InCred", "Avanse", "Prodigy Finance", "ICICI Bank"]
    cities = ["BANGALORE", "PUNE", "HYDERABAD", "DELHI", "KOLKATA", "MUMBAI"]
    
    # --- Table A: Disbursements Ledger ---
    rows = []
    student_counter = 1000
    
    # Generate historical data spanning 2021 to 2024
    for year in [2021, 2022, 2023, 2024]:
        # Scale up number of students over the years to match growth
        num_students = {2021: 450, 2022: 400, 2023: 700, 2024: 1300}[year]
        
        for _ in range(num_students):
            student_counter += 1
            city = np.random.choice(cities, p=[0.25, 0.20, 0.15, 0.15, 0.10, 0.15])
            lender = np.random.choice(lenders, p=[0.35, 0.20, 0.15, 0.20, 0.10])
            
            # Base sanction amount ranges from 20L to 60L INR
            sanction_amt = np.random.randint(2000000, 6000000)
            
            # Determine conversion (Drawdown leakage baseline per city)
            drawdown_prob = {"BANGALORE": 0.63, "PUNE": 0.56, "HYDERABAD": 0.51, 
                             "DELHI": 0.45, "KOLKATA": 0.46, "MUMBAI": 0.40}[city]
            
            converted = np.random.rand() < drawdown_prob
            
            if converted:
                # Simulating tranches (1st year, 2nd year payouts)
                num_tranches = np.random.choice([1, 2], p=[0.4, 0.6])
                for t in range(1, num_tranches + 1):
                    # Tranches spread out across years
                    disb_year = year + (t - 1)
                    if disb_year > 2024: continue
                    
                    # Random date within that intake cycle (July-Oct or Jan-Feb)
                    month = np.random.choice([1, 2, 7, 8, 9, 10])
                    day = np.random.randint(1, 28)
                    disb_date = datetime(disb_year, month, day)
                    
                    # Tranche splitting the sanction amount roughly
                    disb_amt = (sanction_amt / num_tranches) * np.random.uniform(0.9, 1.1)
                    
                    rows.append({
                        "student_id": f"YK-{student_counter}",
                        "student_city": city,
                        "lending_partner": lender,
                        "sanction_amount_inr": sanction_amt,
                        "disbursement_date": disb_date,
                        "disbursed_amount_inr": disb_amt,
                        "tranche_number": t,
                        "intake_year": year # Year the student originally onboarded
                    })
            else:
                # Keep tracking of failed drawdowns to capture the leakage metric
                rows.append({
                    "student_id": f"YK-{student_counter}",
                    "student_city": city,
                    "lending_partner": lender,
                    "sanction_amount_inr": sanction_amt,
                    "disbursement_date": pd.NaT,
                    "disbursed_amount_inr": 0,
                    "tranche_number": 0,
                    "intake_year": year
                })
                
    df_disb = pd.DataFrame(rows)
    
    # --- Table C: Ancillary / Event B2B Revenue ---
    event_rows = []
    events = ["Fall Intake Fair", "Spring Intake Fair", "Premium Loan Webinar", "Exclusive Partner Summit"]
    event_id = 1
    
    for year in [2021, 2022, 2023, 2024]:
        for ev in events:
            for lender in lenders:
                # Higher event sponsorship spending as years progress
                multiplier = {2021: 1.0, 2022: 1.2, 2023: 2.0, 2024: 3.5}[year]
                amt = np.random.randint(50000, 200000) * multiplier
                
                event_rows.append({
                    "event_id": f"EV-{event_id}",
                    "event_name": f"{ev} {year}",
                    "event_date": datetime(year, np.random.choice([4, 5, 11, 12]), np.random.randint(1, 28)),
                    "lending_partner": lender,
                    "revenue_type": np.random.choice(["Premium Booth Slot", "Webinar Sponsor", "Database Branding"]),
                    "amount_earned_inr": amt
                })
                event_id += 1
                
    df_events = pd.DataFrame(event_rows)
    return df_disb, df_events

df_disbursements, df_events = generate_mock_data()

# ==========================================
# 3. STATIC LENDER SLAB CONTRACT LOOKUP ENGINE
# ==========================================
def calculate_commission_rate(partner, total_volume_inr):
    # Dynamic slab rules: Base volume threshold checks in Crores (1 Cr = 10,000,000)
    vol_cr = total_volume_inr / 10000000
    
    # Dynamic logic mapping out standard fintech volume-tier accelerators
    if vol_cr <= 150:
        return 0.0125  # 1.25%
    elif vol_cr <= 400:
        return 0.0150  # 1.50%
    elif vol_cr <= 600:
        return 0.0175  # 1.75%
    else:
        return 0.0200  # 2.00%

# ==========================================
# 4. SIDEBAR CONTROL PANEL
# ==========================================
st.sidebar.title("Navigation Filters")

# Global Filters
year_filter = st.sidebar.selectbox("Select Operational Year", [2024, 2023, 2022, 2021])
partner_options = list(df_disbursements['lending_partner'].unique())
partner_filter = st.sidebar.multiselect("Filter Lending Partners", options=partner_options, default=partner_options)

# Filter Data Pipelines based on user inputs
df_disb_filtered = df_disbursements[
    ((df_disbursements['disbursement_date'].dt.year == year_filter) | (df_disbursements['disbursement_date'].isna())) &
    (df_disbursements['lending_partner'].isin(partner_filter))
].copy()

df_events_filtered = df_events[
    (df_events['event_date'].dt.year == year_filter) &
    (df_events['lending_partner'].isin(partner_filter))
].copy()

# ==========================================
# 5. BUSINESS LOGIC CORE AGGREGATIONS
# ==========================================
# Aggregate Volume to determine Dynamic Slab Rates per Lender
lender_volumes = df_disbursements[df_disbursements['disbursement_date'].dt.year == year_filter].groupby('lending_partner')['disbursed_amount_inr'].sum().to_dict()

# Apply Slab checks dynamically over the actual filtered frame
def compute_row_revenue(row):
    if pd.isna(row['disbursement_date']):
        return 0
    total_partner_vol = lender_volumes.get(row['lending_partner'], 0)
    rate = calculate_commission_rate(row['lending_partner'], total_partner_vol)
    return row['disbursed_amount_inr'] * rate

df_disb_filtered['revenue_earned_inr'] = df_disb_filtered.apply(compute_row_revenue, axis=1)

# Summary numbers
total_disb_volume = df_disb_filtered['disbursed_amount_inr'].sum()
total_comm_revenue = df_disb_filtered['revenue_earned_inr'].sum()
total_event_revenue = df_events_filtered['amount_earned_inr'].sum()
gross_vertical_revenue = total_comm_revenue + total_event_revenue
total_students_funded = df_disb_filtered[df_disb_filtered['disbursed_amount_inr'] > 0]['student_id'].nunique()

# ==========================================
# 6. APP BODY LAYOUT & TABS
# ==========================================
st.title("📊 Yocket Funnel Finance & Disbursement Command Center")
st.caption(f"Showing localized metrics for Financial Year Running Period: {year_filter}")
st.divider() # Corrected from st.hr()

# --- Top Level Dashboard Core Summary KPIs ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="Total Disbursed Volume", value=f"₹{total_disb_volume/10000000:.2f} Cr")
with col2:
    st.metric(label="Gross Vertical Revenue", value=f"₹{gross_vertical_revenue/10000000:.2f} Cr", delta=f"Events: ₹{total_event_revenue/100000:,.0f} L")
with col3:
    st.metric(label="Blended Portfolio Take-Rate", value=f"{(total_comm_revenue / total_disb_volume * 100 if total_disb_volume > 0 else 0):.3f}%")
with col4:
    st.metric(label="Unique Funded Students", value=f"{total_students_funded:,} Students")

st.write("##")

# --- Primary Tab Layout Architecture ---
tab1, tab2, tab3 = st.tabs(["🏛️ Executive Finance Insights", "📍 Regional Leakage Analysis", "🤝 Partner Management Matrix"])

# ------------------------------------------
# TAB 1: EXECUTIVE FINANCE INSIGHTS
# ------------------------------------------
with tab1:
    st.subheader("Macro Level Growth Trajectory")
    
    # Pre-build full time series historical metrics up to selected period
    hist_growth = []
    for y in [2021, 2022, 2023, 2024]:
        df_y = df_disbursements[df_disbursements['disbursement_date'].dt.year == y]
        vol = df_y['disbursed_amount_inr'].sum() / 10000000
        count = df_y[df_y['disbursed_amount_inr'] > 0]['student_id'].nunique()
        hist_growth.append({"Year": str(y), "Volume (Crs)": vol, "Students Funded": count})
    df_hist = pd.DataFrame(hist_growth)

    # Visual 1: Dual-Axis Combo Chart (Plotly Object Engine)
    fig_growth = go.Figure()
    fig_growth.add_trace(go.Bar(
        x=df_hist["Year"], y=df_hist["Volume (Crs)"],
        name="Disbursement Volume (Crs)", marker_color='#ff9800', yaxis='y1'
    ))
    fig_growth.add_trace(go.Scatter(
        x=df_hist["Year"], y=df_hist["Students Funded"],
        name="Students Count", marker_color='#1f77b4', mode='lines+markers', yaxis='y2'
    ))
    fig_growth.update_layout(
        title="YoY Velocity: Capital Scale vs Student Count Volume",
        yaxis=dict(title="Volume in Crores (INR)", side="left"),
        yaxis2=dict(title="Funded Headcount", side="right", overlaying="y", showgrid=False),
        legend=dict(x=0.01, y=0.99),
        template="plotly_white"
    )
    st.plotly_chart(fig_growth, use_container_width=True)
    
    st.divider() # Corrected from st.hr()
    
    # Section: Split showing Fresh Pipeline versus Compound Tranche Inflows
    st.subheader("Compounding Volume Splitting Structure")
    df_active_disb = df_disb_filtered[df_disb_filtered['disbursed_amount_inr'] > 0].copy()
    
    if not df_active_disb.empty:
        # Calculate Fresh vs Tranche categories based on Original Intake Year vs Active Disbursement Year
        df_active_disb['Volume Type'] = np.where(df_active_disb['intake_year'] == year_filter, "Fresh Student Volume", "Recurring Tranche (Cohort Carryover)")
        
        fig_tranche = px.bar(
            df_active_disb, x="lending_partner", y="disbursed_amount_inr", color="Volume Type",
            title="Revenue Runway Profile: Fresh Onboardings vs Legacy Semester Tranches",
            labels={"disbursed_amount_inr": "Total Volume (INR)", "lending_partner": "Lender"},
            barmode="stack", color_discrete_sequence=["#2ca02c", "#9467bd"], template="plotly_white"
        )
        st.plotly_chart(fig_tranche, use_container_width=True)
    else:
        st.info("No active disbursements for the selected filters.")

# ------------------------------------------
# TAB 2: REGIONAL LEAKAGE ANALYSIS
# ------------------------------------------
with tab2:
    st.subheader("Funnel Conversion Vulnerability Matrix (Sanction vs Drawdown)")
    st.info("💡 Real-time leak metric diagnostic tracking where approved loan files are dropping out before real money draws down.")
    
    # Create regional aggregation frame
    region_aggs = df_disb_filtered.groupby("student_city").agg(
        Total_Sanctioned=("sanction_amount_inr", "sum"),
        Total_Disbursed=("disbursed_amount_inr", "sum")
    ).reset_index()
    
    region_aggs['Conversion_Rate'] = (region_aggs['Total_Disbursed'] / region_aggs['Total_Sanctioned']) * 100
    region_aggs = region_aggs.sort_values(by="Conversion_Rate", ascending=False)
    
    # Visual: Grouped Side-by-Side comparison bars
    fig_leak = go.Figure()
    fig_leak.add_trace(go.Bar(
        x=region_aggs["student_city"], y=region_aggs["Total_Sanctioned"],
        name="Pipeline Sanctioned Amount", marker_color="#aec7e8"
    ))
    fig_leak.add_trace(go.Bar(
        x=region_aggs["student_city"], y=region_aggs["Total_Disbursed"],
        name="Realized Drawdown Volume", marker_color="#1f77b4"
    ))
    fig_leak.update_layout(
        barmode='group', title="Regional Target Slip and Conversion Performance Ledger",
        yaxis_title="Capital Value (INR)", template="plotly_white"
    )
    st.plotly_chart(fig_leak, use_container_width=True)
    
    # Callout Matrix Grid elements
    st.write("### Conversion Benchmarks by Regional Branches")
    cols = st.columns(len(region_aggs))
    for index, row in region_aggs.iterrows():
        with cols[index % len(region_aggs)]:
            status_color = "normal" if row['Conversion_Rate'] >= 50 else "inverse"
            st.metric(
                label=row['student_city'], 
                value=f"{row['Conversion_Rate']:.1f}%", 
                delta=f"Lost: ₹{(row['Total_Sanctioned']-row['Total_Disbursed'])/10000000:.1f} Cr",
                delta_color=status_color
            )

# ------------------------------------------
# TAB 3: PARTNER MANAGEMENT MATRIX
# ------------------------------------------
with tab3:
    st.subheader("Lender Portfolio Revenue Structure")
    
    # Build consolidated Portfolio Matrix (B2B Partner Matrix)
    partner_disb = df_disb_filtered.groupby("lending_partner").agg(
        Loan_Volume=("disbursed_amount_inr", "sum"),
        Commission_Rev=("revenue_earned_inr", "sum")
    ).reset_index()
    
    partner_ev = df_events_filtered.groupby("lending_partner").agg(
        Event_Rev=("amount_earned_inr", "sum")
    ).reset_index()
    
    partner_matrix = pd.merge(partner_disb, partner_ev, on="lending_partner", how="outer").fillna(0)
    partner_matrix["Total_Contribution"] = partner_matrix["Commission_Rev"] + partner_matrix["Event_Rev"]
    
    col_left, col_right = st.columns([3, 2])
    
    with col_left:
        # Visual: Comprehensive Partner Value Matrix Map Scatter Chart
        fig_scatter = px.scatter(
            partner_matrix, x="Loan_Volume", y="Event_Rev", size="Total_Contribution",
            text="lending_partner", title="Partner Quadrant Value Alignment Map",
            labels={"Loan_Volume": "Total Loan Capital Disbursed (INR)", "Event_Rev": "Ancillary Marketing/Event Payouts (INR)"},
            template="plotly_white", size_max=40
        )
        fig_scatter.update_traces(textposition='top center')
        st.plotly_chart(fig_scatter, use_container_width=True)
        
    with col_right:
        st.write("### Dynamic Commission Slab Targets")
        # Generate interactive visual indicator showing contract goal steps
        for lender in partner_options:
            vol_cr = lender_volumes.get(lender, 0) / 10000000
            
            # Determine target thresholds
            if vol_cr <= 150: next_tier, target = "1.50%", 150
            elif vol_cr <= 400: next_tier, target = "1.75%", 400
            elif vol_cr <= 600: next_tier, target = "2.00%", 600
            else: next_tier, target = "Max Rate Unlocked", 1000
            
            progress = min(vol_cr / target, 1.0) if target > 0 else 1.0
            
            st.write(f"**{lender}** - Current: `{vol_cr:.1f} Cr` / Target: `{target} Cr` to unlock `{next_tier}`")
            st.progress(progress)
            
    st.divider() # Corrected from st.hr()
    st.subheader("Unified Transaction Audit Registry")
    
    # Display the final unified transactional dataframe output for direct manual checks
    audit_df = df_disb_filtered[df_disb_filtered['disbursed_amount_inr'] > 0][
        ["student_id", "student_city", "lending_partner", "sanction_amount_inr", "disbursement_date", "disbursed_amount_inr", "tranche_number", "revenue_earned_inr"]
    ].sort_values(by="disbursement_date", ascending=False)
    
    st.dataframe(audit_df, use_container_width=True)
