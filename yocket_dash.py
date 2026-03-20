import streamlit as st
import pandas as pd
import plotly.express as px

# --- PAGE SETUP ---
st.set_page_config(page_title="Yocket Lead Analyst", layout="wide")
st.title("🚀 Yocket Finance: Super-Dashboard")

# --- SIDEBAR & UPLOAD ---
st.sidebar.header("Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload Metabase CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # --- AUTOMATIC COLUMN TRANSLATOR ---
    rename_map = {
        'OwnerIdName': 'owner_id_name',
        'New_PS': 'current_prospect_stage',
        'ConnectedDateBucket': 'lcb_bucket',
        'CallDateBucket': 'ltv_bucket',
        'ProspectID': 'lead_id',
        'Aging_Days': 'lead_aging',
        'reason': 'lost_reason',
        'FollowUpDate': 'follow_up_date',
        'NF_task_fin': 'task_source',
        'mx_Admit_recieved': 'admit_status'
    }
    df = df.rename(columns=rename_map)
    
    # --- DATA CLEANUP ---
    if 'current_prospect_stage' in df.columns:
        df['current_prospect_stage'] = df['current_prospect_stage'].astype(str).str.strip()
    
    if 'lead_aging' not in df.columns: df['lead_aging'] = 0 
    else: df['lead_aging'] = pd.to_numeric(df['lead_aging'], errors='coerce').fillna(0)
        
    if 'lost_reason' not in df.columns: df['lost_reason'] = 'Active'
    else: df['lost_reason'] = df['lost_reason'].fillna('Active')

    if 'lcb_bucket' not in df.columns: df['lcb_bucket'] = "Unknown"
    
    # Convert essential dates for Velocity math
    date_columns = ['Qualified_Date', 'Sanction_Date', 'follow_up_date']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    today = pd.Timestamp.today()

    # Sidebar Filters
    st.sidebar.markdown("### Filters")
    if 'owner_id_name' in df.columns:
        all_rms = df['owner_id_name'].dropna().unique().tolist()
        selected_rms = st.sidebar.multiselect("Select RMs", all_rms, default=all_rms)
        filtered_df = df[df['owner_id_name'].isin(selected_rms)]
    else:
        filtered_df = df
        all_rms = []

    active_df = filtered_df[~filtered_df['current_prospect_stage'].isin(['J. Lost', 'Others'])]
    
    # Create Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Funnel & Aging", "🚨 RM Scorecard", "🛡️ Integrity Audit", "🧠 Deep Insights"])

    # ==========================================
    # TAB 1: FUNNEL & AGING
    # ==========================================
    with tab1:
        st.markdown("### Key Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        total_active_leads = len(active_df)
        disbursed_leads = len(filtered_df[filtered_df['current_prospect_stage'] == 'I. Disbursed'])
        total_lost = len(filtered_df[filtered_df['current_prospect_stage'] == 'J. Lost'])
        conversion_rate = (disbursed_leads / total_active_leads) * 100 if total_active_leads > 0 else 0
        
        high_risk_lcb = len(active_df[active_df['lcb_bucket'].str.contains('More than 15|Not Connected', na=False, case=False)])
        high_risk_percent = (high_risk_lcb / total_active_leads) * 100 if total_active_leads > 0 else 0

        col1.metric("Total Active Leads", total_active_leads)
        col2.metric("System Conversion Rate", f"{conversion_rate:.1f}%")
        
        if high_risk_percent > 20: col3.error(f"High Risk LCB: {high_risk_percent:.1f}% ⚠️")
        else: col3.metric("High Risk LCB", f"{high_risk_percent:.1f}%")
            
        col4.metric("Total Leads Lost", total_lost)
        st.divider()

        colA, colB = st.columns(2)
        yocket_order = ['A. Lead Qualified', 'B. App not started', 'C. App Start', 'D. Ready To Share',
                        'E. Bank Prospect', 'F. Login', 'G. Sanction', 'H. PF Paid', 'I. Disbursed']

        with colA:
            stage_counts = filtered_df['current_prospect_stage'].value_counts().reset_index()
            stage_counts.columns = ['Stage', 'Count']
            funnel_data = stage_counts[stage_counts['Stage'].isin(yocket_order)].copy()
            funnel_data['Stage'] = pd.Categorical(funnel_data['Stage'], categories=yocket_order, ordered=True)
            funnel_data = funnel_data.sort_values('Stage').dropna()
            if not funnel_data.empty:
                fig_funnel = px.funnel(funnel_data, x='Count', y='Stage', title="Funnel Drop-off", color_discrete_sequence=['#4285F4'])
                st.plotly_chart(fig_funnel, use_container_width=True)

        with colB:
            aging_df = active_df.groupby('current_prospect_stage')['lead_aging'].mean().reset_index()
            if not aging_df.empty:
                aging_df['current_prospect_stage'] = pd.Categorical(aging_df['current_prospect_stage'], categories=yocket_order, ordered=True)
                aging_df = aging_df.sort_values('current_prospect_stage').dropna()
                fig_aging = px.bar(aging_df, x='current_prospect_stage', y='lead_aging', title="Avg Aging by Stage (Days)", color='lead_aging', color_continuous_scale='Reds')
                st.plotly_chart(fig_aging, use_container_width=True)

    # ==========================================
    # TAB 2: RM RISK SCORECARD
    # ==========================================
    with tab2:
        st.markdown("### 🚨 The RM Penalty Matrix")
        
        rm_stats = []
        for rm in selected_rms:
            rm_data = df[df['owner_id_name'] == rm]
            rm_active = rm_data[~rm_data['current_prospect_stage'].isin(['J. Lost', 'Others'])]
            active_count = len(rm_active)
            if active_count == 0: continue
            
            ghosted = len(rm_active[rm_active['lcb_bucket'].str.contains('More than 15|Not Connected', na=False, case=False)])
            ghost_pct = (ghosted / active_count) * 100
            avg_aging = rm_active['lead_aging'].mean()
            missed_fu = len(rm_active[rm_active['follow_up_date'] < today]) if 'follow_up_date' in rm_active.columns else 0
            
            lost_count = len(rm_data[rm_data['current_prospect_stage'] == 'J. Lost'])
            total_assigned = len(rm_data)
            loss_pct = (lost_count / total_assigned) * 100 if total_assigned > 0 else 0
            
            rm_stats.append({'RM Name': rm, 'Active Leads': active_count, 'Ghosted %': ghost_pct, 
                             'Avg Aging (Days)': avg_aging, 'Missed FUs': missed_fu, 'Loss Rate %': loss_pct})
            
        if rm_stats:
            scorecard_df = pd.DataFrame(rm_stats)
            st.dataframe(scorecard_df.style.background_gradient(cmap='Reds', subset=['Ghosted %', 'Avg Aging (Days)', 'Missed FUs', 'Loss Rate %'])
                         .format({'Ghosted %': '{:.1f}%', 'Avg Aging (Days)': '{:.1f}', 'Loss Rate %': '{:.1f}%'}),
                         use_container_width=True)

    # ==========================================
    # TAB 3: INTEGRITY AUDIT
    # ==========================================
    with tab3:
        st.markdown("### 🛡️ Process Integrity Checks")
        colX, colY = st.columns(2)
        
        with colX:
            st.subheader("Missed Follow-ups")
            if 'follow_up_date' in active_df.columns:
                missed = active_df[active_df['follow_up_date'] < today]
                if not missed.empty:
                    st.table(missed.groupby("owner_id_name").size().reset_index(name="Missed FUs").sort_values("Missed FUs", ascending=False).head(5))
                else:
                    st.success("No missed follow-ups!")
                    
        with colY:
            st.subheader("High Connection Risk (>15 Days LCB)")
            ghost_leads = active_df[active_df['lcb_bucket'].str.contains('More than 15|Not Connected', na=False, case=False)]
            if not ghost_leads.empty:
                st.table(ghost_leads.groupby("owner_id_name").size().reset_index(name="Ghosted").sort_values("Ghosted", ascending=False).head(5))
            else:
                st.success("No high risk leads!")

    # ==========================================
    # TAB 4: DEEP INSIGHTS (Velocity & Predictive)
    # ==========================================
    with tab4:
        st.markdown("### 🧠 Advanced Analytics Engine")
        st.divider()
        
        col_ins1, col_ins2 = st.columns(2)
        
        # INSIGHT 1: PIPELINE VELOCITY
        with col_ins1:
            st.markdown("#### ⏱️ Pipeline Velocity (Days to Sanction)")
            if 'Qualified_Date' in df.columns and 'Sanction_Date' in df.columns:
                # Filter to leads that actually reached sanction
                sanctioned_df = df[df['Sanction_Date'].notna() & df['Qualified_Date'].notna()].copy()
                sanctioned_df['Days_to_Sanction'] = (sanctioned_df['Sanction_Date'] - sanctioned_df['Qualified_Date']).dt.days
                
                # Remove weird negative data if dates were entered wrong
                sanctioned_df = sanctioned_df[sanctioned_df['Days_to_Sanction'] >= 0]
                
                if not sanctioned_df.empty:
                    median_days = sanctioned_df['Days_to_Sanction'].median()
                    st.metric("Median Days (Qualified ➡️ Sanction)", f"{median_days:.0f} Days")
                    
                    fig_vel = px.histogram(sanctioned_df, x='Days_to_Sanction', nbins=20, 
                                           title="Distribution of Time to Sanction", color_discrete_sequence=['#34A853'])
                    st.plotly_chart(fig_vel, use_container_width=True)
                else:
                    st.info("Not enough data to calculate velocity.")
            else:
                st.warning("Missing Date columns for Velocity check.")

        # INSIGHT 2: THE ADMIT MULTIPLIER
        with col_ins2:
            st.markdown("#### 🎓 Admit Status Impact")
            st.write("Does having an admit significantly increase the chance of getting a Sanction/Disbursal?")
            
            if 'admit_status' in df.columns:
                # define "Success" as reaching Sanction, PF, or Disbursed
                success_stages = ['G. Sanction', 'H. PF Paid', 'I. Disbursed']
                df['Is_Success'] = df['current_prospect_stage'].isin(success_stages).astype(int)
                
                admit_stats = df.groupby('admit_status')['Is_Success'].agg(['count', 'mean']).reset_index()
                admit_stats = admit_stats[admit_stats['count'] > 5] # filter noise
                admit_stats['Win Rate %'] = (admit_stats['mean'] * 100).round(1)
                
                fig_admit = px.bar(admit_stats, x='admit_status', y='Win Rate %', text='Win Rate %',
                                   title="Win Rate by Admit Status", color='Win Rate %', color_continuous_scale='Blues')
                fig_admit.update_traces(textposition='outside')
                st.plotly_chart(fig_admit, use_container_width=True)
            else:
                st.warning("Missing admit_status column.")

        st.divider()

        # INSIGHT 3: TOXIC SOURCES
        st.markdown("#### ☣️ Toxic Sources (Highest Loss Rates)")
        if 'Subsource' in df.columns:
            source_stats = df.groupby('Subsource').agg(
                Total_Leads=('lead_id', 'count'),
                Lost_Leads=('current_prospect_stage', lambda x: (x == 'J. Lost').sum())
            ).reset_index()
            
            source_stats['Loss Rate %'] = ((source_stats['Lost_Leads'] / source_stats['Total_Leads']) * 100).round(1)
            # Filter for sources that actually have volume
            toxic_sources = source_stats[source_stats['Total_Leads'] > 10].sort_values('Loss Rate %', ascending=False).head(5)
            
            fig_toxic = px.bar(toxic_sources, x='Loss Rate %', y='Subsource', orientation='h', 
                               title="Top 5 Subsources with the Highest 'Lost' Rate", 
                               text='Loss Rate %', color='Loss Rate %', color_continuous_scale='Reds')
            st.plotly_chart(fig_toxic, use_container_width=True)

else:
    st.info("Upload your Yocket Metabase CSV in the sidebar to generate the dashboard.")