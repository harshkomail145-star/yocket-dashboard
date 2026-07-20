import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="MPL Cohort Funnel", layout="wide")

# ==========================================
# DATA LOADING & MOCKING (SUPERLOANS SoR)
# ==========================================
@st.cache_data(ttl=3600)
def load_cohort_data():
    """
    Simulates pulling cohort data directly from SuperLoans (Sole SoR).
    Strictly enforces Master Stage / Bank Stage separation and locking rules.
    """
    np.random.seed(42)
    n_leads = 2000

    # 1. Master Lead Record (Student Level)
    # The requested non-finco sources
    sources = ['bulk leads', 'pre-sales leads', 'product leads']
    
    # The requested Master Stages (Monotonic progression)
    master_stages = [
        'Lead Qualified', 'App Started', 'Ready to Share', 
        'Bank Prospect', 'Sanction', 'PF'
    ]
    
    # Generate mock student records
    master_df = pd.DataFrame({
        'student_id': [f"STU-{i:04d}" for i in range(n_leads)],
        'source': np.random.choice(sources, n_leads, p=[0.5, 0.3, 0.2]),
        'intake': np.random.choice(['Fall 26', 'Spring 26'], n_leads),
        'highest_master_stage': np.random.choice(master_stages, n_leads, p=[0.2, 0.15, 0.15, 0.2, 0.2, 0.1]),
        'lifecycle_state': np.random.choice(['Active', 'Lost'], n_leads, p=[0.8, 0.2])
    })

    # ENFORCE MBC LOCKING INVARIANTS:
    # Rule 1: Intake is immutable after PF. 
    master_df['intake_locked'] = master_df['highest_master_stage'] == 'PF'
    # Rule 2: Source is mutable before BP (inactivity rule), but immutable after BP.
    post_bp_stages = ['Bank Prospect', 'Sanction', 'PF']
    master_df['source_locked'] = master_df['highest_master_stage'].isin(post_bp_stages)

    # 2. Bank Sub-Records (Parallel tracking post-BP)
    # Only generated for students who reached at least Bank Prospect
    bp_plus_students = master_df[master_df['source_locked']]['student_id']
    
    bank_records = []
    banks = ['SBI', 'Avanse', 'Credila', 'Auxilo']
    bank_outcomes = ['Login', 'Sanction', 'PF', 'Hold', 'Credit Rejected', 'Duplicate']
    
    for student in bp_plus_students:
        # A student can have multiple bank tracks simultaneously (multi-login structural advantage)
        assigned_banks = np.random.choice(banks, np.random.randint(1, 4), replace=False)
        for bank in assigned_banks:
            bank_records.append({
                'student_id': student,
                'bank_name': bank,
                'bank_stage': np.random.choice(bank_outcomes)
            })
            
    bank_df = pd.DataFrame(bank_records)

    return master_df, bank_df, master_stages

master_df, bank_df, stage_order = load_cohort_data()

# ==========================================
# SIDEBAR FILTERS
# ==========================================
st.sidebar.title("Cohort Filters")
st.sidebar.caption("Data Source: SuperLoans DB")

selected_intake = st.sidebar.multiselect("Intake Season", master_df['intake'].unique(), default=master_df['intake'].unique())
selected_sources = st.sidebar.multiselect("Lead Source", master_df['source'].unique(), default=master_df['source'].unique())
selected_lifecycle = st.sidebar.radio("Lifecycle State", ['All', 'Active', 'Lost'])

# Apply filters
filtered_df = master_df[
    (master_df['intake'].isin(selected_intake)) & 
    (master_df['source'].isin(selected_sources))
]

if selected_lifecycle != 'All':
    filtered_df = filtered_df[filtered_df['lifecycle_state'] == selected_lifecycle]

# ==========================================
# METRICS & DASHBOARD HEADER
# ==========================================
st.title("Non-Finco Cohort Funnel")
st.markdown("Tracking highest positive progression per student based strictly on SuperLoans stage history.")

# Calculate true cohort funnel (Cumulative sum reverse)
# Because Master Stage is non-downgrading, a student at "PF" inherently reached "Sanction", "BP", etc.
stage_counts = filtered_df['highest_master_stage'].value_counts().reindex(stage_order).fillna(0)
cohort_funnel_counts = [stage_counts.loc[stage:].sum() for stage in stage_order]

col1, col2, col3 = st.columns(3)
col1.metric("Total Cohort Leads (LQ)", cohort_funnel_counts[0])
col2.metric("Total Reached BP", cohort_funnel_counts[3])
col3.metric("Total Reached PF", cohort_funnel_counts[5])

st.markdown("---")

# ==========================================
# MASTER COHORT FUNNEL
# ==========================================
st.subheader("Master Stage Funnel (Student Level)")
st.caption("Monotonic cohort progression. A student at PF is counted in all preceding stages.")

fig_funnel = go.Figure(go.Funnel(
    y=stage_order,
    x=cohort_funnel_counts,
    textinfo="value+percent initial+percent previous",
    marker={"color": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]}
))

fig_funnel.update_layout(margin=dict(t=20, b=20))
st.plotly_chart(fig_funnel, use_container_width=True)

# ==========================================
# SOURCE BREAKDOWN & BANK OUTCOMES
# ==========================================
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Source Conversion to BP")
    st.caption("Which non-finco sources are yielding shareable prospects?")
    
    # Calculate conversion rate to BP per source
    source_metrics = []
    for source in filtered_df['source'].unique():
        source_data = filtered_df[filtered_df['source'] == source]
        total = len(source_data)
        reached_bp = len(source_data[source_data['highest_master_stage'].isin(['Bank Prospect', 'Sanction', 'PF'])])
        conversion = (reached_bp / total * 100) if total > 0 else 0
        source_metrics.append({'Source': source, 'Total Leads': total, 'Reached BP': reached_bp, 'Conv to BP (%)': round(conversion, 2)})
        
    st.dataframe(pd.DataFrame(source_metrics), hide_index=True, use_container_width=True)

with col_b:
    st.subheader("Parallel Bank Stages (Post-BP)")
    st.caption("Bank sub-record outcomes (includes negative dispositions).")
    
    # Filter bank records for the current master cohort
    cohort_bank_df = bank_df[bank_df['student_id'].isin(filtered_df['student_id'])]
    
    if not cohort_bank_df.empty:
        bank_summary = cohort_bank_df.groupby(['bank_name', 'bank_stage']).size().reset_index(name='count')
        fig_bank = px.bar(bank_summary, x='bank_name', y='count', color='bank_stage', barmode='group')
        fig_bank.update_layout(margin=dict(t=20, b=20))
        st.plotly_chart(fig_bank, use_container_width=True)
    else:
        st.info("No leads in the current filtered cohort have reached Bank Prospect yet.")
