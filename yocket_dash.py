import streamlit as st
import pandas as pd
import plotly.express as px

# --- PAGE SETUP ---
st.set_page_config(page_title="Yocket PF Tracker", layout="wide")
st.title("🎯 Yocket Finance: PF & Login Command Center")

# --- SIDEBAR ---
st.sidebar.header("Control Center")
uploaded_file = st.sidebar.file_uploader("Upload Metabase CSV", type=["csv"])

st.sidebar.divider()
st.sidebar.subheader("🏁 PF Target Settings")
pf_target = st.sidebar.number_input("Monthly PF Target", min_value=1, value=50)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # --- DYNAMIC DATE CLEANING ---
    # Convert all possible date columns to datetime
    date_cols = ['Qualified_Date', 'Login_Date', 'Sanction_Date', 'PF_Paid_Date', 'Disbursed_Date']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # --- THE "JOURNEY LOGIC" ENGINE ---
    # A lead hit LOGIN if it has a Login Date OR any date that comes after Login
    df['has_login'] = df[['Login_Date', 'Sanction_Date', 'PF_Paid_Date', 'Disbursed_Date']].notna().any(axis=1)
    
    # A lead hit PF if it has a PF Date OR a Disbursed Date
    df['has_pf'] = df[['PF_Paid_Date', 'Disbursed_Date']].notna().any(axis=1)

    # --- METRICS ---
    total_pfs = df['has_pf'].sum()
    total_logins = df['has_login'].sum()
    
    # --- TABS ---
    tab_pf, tab_rm, tab_velocity = st.tabs(["💰 PF Target Tracker", "🏆 RM Leaderboard", "⏱️ Stage Velocity"])

    # ==========================================
    # TAB 1: PF TARGET TRACKER
    # ==========================================
    with tab_pf:
        col1, col2, col3 = st.columns(3)
        pf_pct = (total_pfs / pf_target)
        
        col1.metric("Total PFs (Based on Dates)", int(total_pfs))
        col2.metric("Target Gap", int(max(0, pf_target - total_pfs)))
        col3.metric("Login to PF Conv.", f"{(total_pfs/total_logins*100):.1f}%" if total_logins > 0 else "0%")

        st.write(f"### PF Target Progress: {pf_pct*100:.1f}%")
        st.progress(min(pf_pct, 1.0))
        if pf_pct >= 1.0: st.balloons()

        # Visualizing the True Date-Based Funnel
        funnel_data = pd.DataFrame({
            'Stage': ['Qualified', 'Login', 'PF', 'Disbursed'],
            'Count': [
                df['Qualified_Date'].notna().sum(),
                total_logins,
                total_pfs,
                df['Disbursed_Date'].notna().sum()
            ]
        })
        fig = px.funnel(funnel_data, x='Count', y='Stage', title="Real-Time Journey (Based on Dates)")
        st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # TAB 2: RM LEADERBOARD (The PF Kings)
    # ==========================================
    with tab_rm:
        st.subheader("🏆 RM Ranking (PF Achievement)")
        
        rm_group = df.groupby('OwnerIdName').agg(
            Total_Qualified=('Qualified_Date', 'count'),
            True_Logins=('has_login', 'sum'),
            True_PFs=('has_pf', 'sum')
        ).reset_index()
        
        # Calculate Conversion: Logins to PF
        rm_group['Login_to_PF_%'] = (rm_group['True_PFs'] / rm_group['True_Logins'] * 100).fillna(0).round(1)
        
        # Filter out RMs with zero logins to clean the leaderboard
        rm_group = rm_group[rm_group['True_Logins'] > 0].sort_values('True_PFs', ascending=False)
        
        st.dataframe(
            rm_group.style.background_gradient(cmap='YlGn', subset=['True_PFs', 'Login_to_PF_%']),
            use_container_width=True,
            hide_index=True
        )

    # ==========================================
    # TAB 3: STAGE VELOCITY (How fast are they?)
    # ==========================================
    with tab_velocity:
        st.subheader("⏱️ Days Taken: Login to PF")
        
        # Only look at leads that have both dates
        vel_df = df[df['Login_Date'].notna() & df['PF_Paid_Date'].notna()].copy()
        vel_df['days_to_pf'] = (vel_df['PF_Paid_Date'] - vel_df['Login_Date']).dt.days
        
        # Filter outliers (negative dates or > 60 days)
        vel_df = vel_df[(vel_df['days_to_pf'] >= 0) & (vel_df['days_to_pf'] <= 60)]
        
        if not vel_df.empty:
            avg_vel = vel_df.groupby('OwnerIdName')['days_to_pf'].mean().reset_index().sort_values('days_to_pf')
            avg_vel.columns = ['RM Name', 'Avg Days (Login to PF)']
            
            fig_vel = px.bar(avg_vel, x='RM Name', y='Avg Days (Login to PF)', 
                             title="Who is the Fastest at collecting PF?",
                             color='Avg Days (Login to PF)', color_continuous_scale='Reds_r')
            st.plotly_chart(fig_vel, use_container_width=True)
        else:
            st.info("Not enough date data to calculate velocity yet.")

else:
    st.info("Upload the CSV to see the Date-Driven PF Leaderboard.")
