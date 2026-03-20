import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Yocket RM Audit", layout="wide")
st.title("🚀 Yocket Finance: Deep RM Insights")

uploaded_file = st.sidebar.file_uploader("Upload Metabase CSV", type=["csv"])
pf_target = st.sidebar.number_input("Monthly PF Target", min_value=1, value=50)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # --- EXACT COLUMN MAPPING ---
    l_col = 'Login_Date'
    p_col = 'PF_Date'
    rm_col = 'OwnerIdName'
    lcb_col = 'ConnectedDateBucket'
    ltv_col = 'CallDateBucket'
    age_col = 'Aging_Days'
    stage_col = 'New_PS'

    # Convert dates
    for c in [l_col, p_col, 'Qualified_Date']:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors='coerce')

    # --- LOGIC ENGINE ---
    df['has_login'] = df[[l_col, 'Sanction_Date', p_col]].notna().any(axis=1)
    df['has_pf'] = df[p_col].notna()
    
    # Define "Ghosted" leads (Not connected in a long time or never)
    risk_buckets = ['E More than 15 Days', 'Not Connected', 'D 12-15 Days']
    df['is_ghosted'] = df[lcb_col].isin(risk_buckets)
    
    # Define "Stagnant" leads (Active leads sitting in one stage > 10 days)
    active_stages = ['A. Lead Qualified', 'B. App not started', 'C. App Start', 'D. Ready To Share', 'E. Bank Prospect']
    df['is_stagnant'] = (df[stage_col].isin(active_stages)) & (df[age_col] > 10)

    # --- UI TABS ---
    tab1, tab2, tab3 = st.tabs(["💰 PF & Login Tracker", "🏆 RM Leaderboard", "🚨 RM Lag Analysis"])

    with tab1:
        t_pf = df['has_pf'].sum()
        t_login = df['has_login'].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total PFs", int(t_pf))
        c2.metric("Total Logins", int(t_login))
        c3.metric("Conv. %", f"{(t_pf/t_login*100):.1f}%" if t_login > 0 else "0%")
        
        progress = min(t_pf / pf_target, 1.0)
        st.write(f"### Target Progress: {progress*100:.1f}%")
        st.progress(progress)

    with tab2:
        st.subheader("Top Performers (Success)")
        rm_success = df.groupby(rm_col).agg(
            Logins=('has_login', 'sum'),
            PFs=('has_pf', 'sum')
        ).reset_index().sort_values('PFs', ascending=False)
        st.dataframe(rm_success.style.background_gradient(cmap='Greens', subset=['PFs']), use_container_width=True)

    with tab3:
        st.subheader("🚨 RM Lagging Metrics (Areas of Improvement)")
        st.write("This table shows which RMs are losing leads due to lack of follow-up or slow processing.")
        
        # Calculate Lagging Stats
        rm_lag = df.groupby(rm_col).agg(
            Total_Active_Leads=(stage_col, lambda x: x.isin(active_stages).sum()),
            Ghosted_Leads=('is_ghosted', 'sum'),
            Stagnant_Leads=('is_stagnant', 'sum'),
            Avg_Aging=(age_col, 'mean')
        ).reset_index()

        # Ghosting Rate: What % of their active pipeline is not being talked to?
        rm_lag['Ghosting_Rate_%'] = (rm_lag['Ghosted_Leads'] / rm_lag['Total_Active_Leads'] * 100).fillna(0).round(1)
        
        # Sort by worst offenders (Highest Ghosting Rate)
        rm_lag = rm_lag.sort_values('Ghosting_Rate_%', ascending=False)

        st.dataframe(
            rm_lag.style.background_gradient(cmap='Reds', subset=['Ghosting_Rate_%', 'Avg_Aging', 'Stagnant_Leads']),
            use_container_width=True,
            hide_index=True
        )

        st.divider()
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.write("#### 👻 Top Ghosters")
            st.write("RMs with the highest % of leads not connected in >12 days.")
            fig_ghost = px.bar(rm_lag.head(5), x=rm_col, y='Ghosting_Rate_%', color='Ghosting_Rate_%', color_continuous_scale='Reds')
            st.plotly_chart(fig_ghost, use_container_width=True)

        with col_b:
            st.write("#### 🐢 Stagnation Kings")
            st.write("RMs whose leads are sitting in the same stage for the longest time.")
            fig_age = px.bar(rm_lag.sort_values('Avg_Aging', ascending=False).head(5), x=rm_col, y='Avg_Aging', color='Avg_Aging', color_continuous_scale='Oranges')
            st.plotly_chart(fig_age, use_container_width=True)

else:
    st.info("Upload the Metabase CSV to start the Lag Analysis.")
