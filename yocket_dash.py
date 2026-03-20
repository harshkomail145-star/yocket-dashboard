import streamlit as st
import pandas as pd
import plotly.express as px

# --- PAGE SETUP ---
st.set_page_config(page_title="Yocket Lead Analyst", layout="wide")
st.title("🚀 Yocket Finance: Performance Hub")

# --- SIDEBAR & UPLOAD ---
st.sidebar.header("Control Center")
uploaded_file = st.sidebar.file_uploader("Upload Metabase CSV", type=["csv"])

# --- NEW: TARGET SETTING ---
st.sidebar.divider()
st.sidebar.subheader("🎯 Monthly Goals")
monthly_target = st.sidebar.number_input("Set Disbursal Target", min_value=1, value=50)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # --- COLUMN TRANSLATOR ---
    rename_map = {
        'OwnerIdName': 'owner_id_name',
        'New_PS': 'current_prospect_stage',
        'ConnectedDateBucket': 'lcb_bucket',
        'ProspectID': 'lead_id',
        'Aging_Days': 'lead_aging',
        'FollowUpDate': 'follow_up_date'
    }
    df = df.rename(columns=rename_map)
    
    # --- CLEANUP ---
    df['current_prospect_stage'] = df['current_prospect_stage'].astype(str).str.strip()
    df['lead_aging'] = pd.to_numeric(df['lead_aging'], errors='coerce').fillna(0)
    today = pd.Timestamp.today()

    # Sidebar RM Filter
    if 'owner_id_name' in df.columns:
        all_rms = df['owner_id_name'].dropna().unique().tolist()
        selected_rms = st.sidebar.multiselect("Filter RMs", all_rms, default=all_rms)
        f_df = df[df['owner_id_name'].isin(selected_rms)]
    else:
        f_df = df

    # --- TABS ---
    tab_goal, tab_board, tab_audit = st.tabs(["🎯 Target Tracker", "🏆 RM Leaderboard", "🛡️ Risk Scorecard"])

    # ==========================================
    # TAB: TARGET TRACKER (Goal Progress)
    # ==========================================
    with tab_goal:
        disbursed_count = len(f_df[f_df['current_prospect_stage'] == 'I. Disbursed'])
        progress = min(disbursed_count / monthly_target, 1.0)
        
        col_m1, col_m2 = st.columns([1, 2])
        with col_m1:
            st.metric("Total Disbursals", disbursed_count)
            st.metric("Target Gap", max(0, monthly_target - disbursed_count))
        
        with col_m2:
            st.write(f"### Overall Target Progress: {progress*100:.1f}%")
            st.progress(progress)
            if progress >= 1.0:
                st.balloons()
                st.success("Target Achieved! 🥂")
        
        # Funnel for visual context
        yocket_order = ['A. Lead Qualified', 'B. App not started', 'C. App Start', 'D. Ready To Share',
                        'E. Bank Prospect', 'F. Login', 'G. Sanction', 'H. PF Paid', 'I. Disbursed']
        stage_counts = f_df['current_prospect_stage'].value_counts().reindex(yocket_order).reset_index()
        stage_counts.columns = ['Stage', 'Count']
        fig_funnel = px.funnel(stage_counts, x='Count', y='Stage', title="Pipeline to Target")
        st.plotly_chart(fig_funnel, use_container_width=True)

    # ==========================================
    # TAB: RM LEADERBOARD (The Competition)
    # ==========================================
    with tab_board:
        st.markdown("### 🏆 Top Closers & Speedsters")
        
        # Calculate scores per RM
        leaderboard = []
        for rm in all_rms:
            rm_data = df[df['owner_id_name'] == rm]
            disbursed = len(rm_data[rm_data['current_prospect_stage'] == 'I. Disbursed'])
            logins = len(rm_data[rm_data['current_prospect_stage'] == 'F. Login'])
            
            # Conversion Speed Score (Lower aging is better)
            active = rm_data[~rm_data['current_prospect_stage'].isin(['J. Lost', 'Others'])]
            avg_speed = active['lead_aging'].mean() if not active.empty else 999
            
            leaderboard.append({
                'RM Name': rm,
                'Disbursals 💰': disbursed,
                'Logins 📑': logins,
                'Avg Lead Age ⏱️': round(avg_speed, 1)
            })
        
        lb_df = pd.DataFrame(leaderboard).sort_values('Disbursals 💰', ascending=False)
        
        # Highlight top 3
        col_top1, col_top2, col_top3 = st.columns(3)
        if len(lb_df) >= 1: col_top1.success(f"🥇 {lb_df.iloc[0]['RM Name']} ({lb_df.iloc[0]['Disbursals 💰']} Disbursed)")
        if len(lb_df) >= 2: col_top2.info(f"🥈 {lb_df.iloc[1]['RM Name']}")
        if len(lb_df) >= 3: col_top3.warning(f"🥉 {lb_df.iloc[2]['RM Name']}")
        
        st.divider()
        st.dataframe(lb_df, use_container_width=True, hide_index=True)

    # ==========================================
    # TAB: RISK SCORECARD (The "Penalty" Matrix)
    # ==========================================
    with tab_audit:
        st.markdown("### 🚨 Accountability Matrix")
        # Reuse your previous Risk Scorecard logic here...
        rm_stats = []
        for rm in all_rms:
            rm_data = df[df['owner_id_name'] == rm]
            rm_active = rm_data[~rm_data['current_prospect_stage'].isin(['J. Lost', 'Others'])]
            if len(rm_active) == 0: continue
            
            ghosted = len(rm_active[rm_active['lcb_bucket'].str.contains('More than 15|Not Connected', na=False, case=False)])
            ghost_pct = (ghosted / len(rm_active)) * 100
            
            rm_stats.append({
                'RM Name': rm,
                'Active Pipeline': len(rm_active),
                'Ghosting Rate %': ghost_pct,
                'Stale Leads (>30d)': len(rm_active[rm_active['lead_aging'] > 30])
            })
            
        if rm_stats:
            scorecard = pd.DataFrame(rm_stats)
            st.dataframe(scorecard.style.background_gradient(cmap='Reds', subset=['Ghosting Rate %', 'Stale Leads (>30d)']), use_container_width=True)

else:
    st.info("Upload your Yocket Metabase CSV to see the Leaderboard!")
