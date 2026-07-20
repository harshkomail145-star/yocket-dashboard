import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

# ==========================================
# PAGE CONFIGURATION & SESSION STATE
# ==========================================
st.set_page_config(page_title="MPL Non-Finco Operations", layout="wide")

if 'last_refresh' not in st.session_state:
    st.session_state['last_refresh'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ==========================================
# DATA LOADING & MOCKING (SUPERLOANS SoR)
# ==========================================
@st.cache_data(ttl=3600)
def load_superloans_data():
    """
    Simulates loading from the SuperLoans DB. 
    In production, replace with Snowflake/Redshift SQL queries.
    Strictly follows MBC: No LeadSquared fields, dual-stage logic applied.
    """
    # 1. Master Student Leads (Student Level)
    master_data = pd.DataFrame({
        'student_id': [f"STU{str(i).zfill(4)}" for i in range(1, 501)],
        'phone': [f"98765{str(i).zfill(5)}" for i in range(1, 501)],
        'source': np.random.choice(['Direct residuals', 'LS', 'GB / CSP B2B'], 500),
        'intake': np.random.choice(['Fall 26', 'Spring 26', 'Spring 27'], 500, p=[0.7, 0.15, 0.15]),
        'master_stage': np.random.choice(
            ['LQ', 'App Started', 'RTS', 'BP', 'Login', 'Sanction', 'PF', 'Disbursed'], 
            500, p=[0.1, 0.1, 0.1, 0.2, 0.2, 0.15, 0.1, 0.05]
        ),
        'lifecycle_state': np.random.choice(['Active', 'Lost'], 500, p=[0.85, 0.15]),
        'last_activity_date': [datetime.now() - timedelta(days=np.random.randint(0, 30)) for _ in range(500)],
        'assigned_rm': np.random.choice(['RM_A', 'RM_B', 'RM_C', 'RM_D'], 500),
        'pf_paid_flag': np.random.choice([True, False], 500, p=[0.15, 0.85])
    })
    
    # Enforce PF Lock Rule: If PF is paid, intake is locked.
    master_data.loc[master_data['master_stage'].isin(['PF', 'Disbursed']), 'pf_paid_flag'] = True

    # 2. Bank Sub-Records (Bank Level - Only exists for BP and beyond)
    bp_plus_students = master_data[master_data['master_stage'].isin(['BP', 'Login', 'Sanction', 'PF', 'Disbursed'])]['student_id']
    bank_data = pd.DataFrame({
        'student_id': np.random.choice(bp_plus_students, len(bp_plus_students) * 2),
        'bank_name': np.random.choice(['SBI', 'Avanse', 'Credila', 'Auxilo', 'InCred'], len(bp_plus_students) * 2),
        'bank_stage': np.random.choice(['BP', 'Login', 'Sanction', 'PF', 'Disbursed', 'Duplicate', 'Hold', 'Credit Rejected'], len(bp_plus_students) * 2),
        'is_doable': True # Doability engine guardrail applied prior to BP
    }).drop_duplicates(subset=['student_id', 'bank_name'])

    # 3. RM Telephony / Activity Logs (SuperLoans Disposition Form)
    activity_data = pd.DataFrame({
        'assigned_rm': ['RM_A', 'RM_B', 'RM_C', 'RM_D'],
        'call_duration_seconds': np.random.randint(5000, 25000, 4),
        'outgoing_dial_counts': np.random.randint(50, 200, 4)
    })
    
    # Calculate Man-hours: Convert duration to minutes before aggregating with dials
    activity_data['calculated_man_hours'] = (activity_data['call_duration_seconds'] / 60) + activity_data['outgoing_dial_counts']

    return master_data, bank_data, activity_data

master_df, bank_df, activity_df = load_superloans_data()

# ==========================================
# SIDEBAR & FILTERS
# ==========================================
st.sidebar.title("MPL Non-Finco Ops")
st.sidebar.caption(f"Last Synced: {st.session_state['last_refresh']}")
st.sidebar.markdown("---")

# Default filter targeted to the current active pipeline
selected_intake = st.sidebar.multiselect("Intake Season", options=master_df['intake'].unique(), default=['Fall 26'])
selected_rm = st.sidebar.multiselect("Assigned RM", options=master_df['assigned_rm'].unique(), default=master_df['assigned_rm'].unique())
selected_lifecycle = st.sidebar.radio("Lifecycle State", options=['Active', 'Lost', 'All'], index=0)

# Apply Filters
filtered_master = master_df[
    (master_df['intake'].isin(selected_intake)) & 
    (master_df['assigned_rm'].isin(selected_rm))
]
if selected_lifecycle != 'All':
    filtered_master = filtered_master[filtered_master['lifecycle_state'] == selected_lifecycle]

# ==========================================
# DASHBOARD HEADER & TOP KPIs
# ==========================================
st.title("Top-to-Bottom Pipeline & SLA Audit")
st.markdown("Monitoring the Master Stage funnel, Bank Stage execution, and RM activity metrics via SuperLoans SoR.")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Leads (LQ+)", len(filtered_master))
col2.metric("RTS (Doability Ready)", len(filtered_master[filtered_master['master_stage'] == 'RTS']))
col3.metric("BP (Shared to Banks)", len(filtered_master[filtered_master['master_stage'].isin(['BP', 'Login', 'Sanction', 'PF', 'Disbursed'])]))
col4.metric("Sanctioned (Master)", len(filtered_master[filtered_master['master_stage'].isin(['Sanction', 'PF', 'Disbursed'])]))
col5.metric("PF Paid (Locked Intake)", len(filtered_master[filtered_master['master_stage'].isin(['PF', 'Disbursed'])]))

st.markdown("---")

# ==========================================
# FUNNEL & PIPELINE VISUALIZATIONS
# ==========================================
col_charts_1, col_charts_2 = st.columns(2)

with col_charts_1:
    st.subheader("Master Stage Funnel (Student Level)")
    st.caption("Monotonic progression. Represents the highest positive stage across any bank track.")
    stage_order = ['LQ', 'App Started', 'RTS', 'BP', 'Login', 'Sanction', 'PF', 'Disbursed']
    funnel_data = filtered_master['master_stage'].value_counts().reindex(stage_order).fillna(0).reset_index()
    funnel_data.columns = ['Stage', 'Count']
    
    fig_funnel = px.funnel(funnel_data, x='Count', y='Stage', color_discrete_sequence=['#1f77b4'])
    st.plotly_chart(fig_funnel, use_container_width=True)

with col_charts_2:
    st.subheader("Bank Stage Pipeline (Sub-Record Level)")
    st.caption("Parallel progression. Tracks specific lender outcomes including negative dispositions.")
    
    # Filter bank data based on the filtered master students
    filtered_bank = bank_df[bank_df['student_id'].isin(filtered_master['student_id'])]
    bank_stage_counts = filtered_bank.groupby(['bank_name', 'bank_stage']).size().reset_index(name='count')
    
    fig_bar = px.bar(bank_stage_counts, x='bank_name', y='count', color='bank_stage', 
                     title="Lender Pipeline Distribution", barmode='stack')
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# ==========================================
# RM ACTIVITY & 9:00 AM SLA HIT-LIST
# ==========================================
col_act_1, col_act_2 = st.columns([1, 2])

with col_act_1:
    st.subheader("RM Activity & Effort")
    st.caption("Derived solely from SuperLoans dispositions. (Duration in mins + Dials)")
    # Filter activity based on selected RMs
    rm_activity = activity_df[activity_df['assigned_rm'].isin(selected_rm)][['assigned_rm', 'call_duration_seconds', 'outgoing_dial_counts', 'calculated_man_hours']]
    st.dataframe(rm_activity, hide_index=True, use_container_width=True)

with col_act_2:
    st.subheader("Daily Audit: 21-Day Pre-BP Inactivity Risk")
    st.caption("Critical leads at risk of source-retagging due to >21 days of no disposition logged.")
    
    # Calculate days inactive
    filtered_master['days_inactive'] = (datetime.now() - filtered_master['last_activity_date']).dt.days
    
    # MBC Rule: Inactivity source-change rule applies ONLY before BP.
    pre_bp_stages = ['LQ', 'App Started', 'RTS']
    hit_list = filtered_master[
        (filtered_master['master_stage'].isin(pre_bp_stages)) & 
        (filtered_master['days_inactive'] >= 21) &
        (filtered_master['lifecycle_state'] == 'Active')
    ].sort_values(by='days_inactive', ascending=False)
    
    st.dataframe(
        hit_list[['student_id', 'master_stage', 'days_inactive', 'source', 'assigned_rm']],
        hide_index=True, 
        use_container_width=True
    )
