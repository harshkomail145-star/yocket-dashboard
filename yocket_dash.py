import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Yocket Date Tracker", layout="wide")
st.title("🎯 Yocket Finance: PF & Login Command Center")

uploaded_file = st.sidebar.file_uploader("Upload Metabase CSV", type=["csv"])
pf_target = st.sidebar.number_input("Monthly PF Target", min_value=1, value=50)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # --- HELPER FUNCTION TO FIND COLUMNS ---
    def find_col(keywords):
        for col in df.columns:
            if any(k.lower() in col.lower() for k in keywords):
                return col
        return None

    # Mapping your Metabase columns automatically
    q_col = find_col(['Qualified_Date', 'Qualified Date'])
    l_col = find_col(['Login_Date', 'Login Date'])
    s_col = find_col(['Sanction_Date', 'Sanction Date'])
    p_col = find_col(['PF_Paid_Date', 'PF Date', 'PF Paid'])
    d_col = find_col(['Disbursed_Date', 'Disbursal Date'])
    rm_col = find_col(['OwnerIdName', 'Owner', 'RM Name'])

    # --- STOP ERROR IF COLUMNS MISSING ---
    required = [l_col, p_col, rm_col]
    if None in required:
        st.error(f"⚠️ Column mismatch! I couldn't find one of these: Login, PF, or RM Name. Your columns are: {list(df.columns)}")
    else:
        # Convert to datetime
        for c in [q_col, l_col, s_col, p_col, d_col]:
            if c: df[c] = pd.to_datetime(df[c], errors='coerce')

        # --- THE JOURNEY LOGIC (Safe version) ---
        # Lead hit Login if it has a Login date OR any later date
        later_than_login = [c for c in [l_col, s_col, p_col, d_col] if c]
        df['has_login'] = df[later_than_login].notna().any(axis=1)
        
        # Lead hit PF if it has a PF date OR Disbursed date
        later_than_pf = [c for c in [p_col, d_col] if c]
        df['has_pf'] = df[later_than_pf].notna().any(axis=1)

        # --- DASHBOARD UI ---
        total_pfs = df['has_pf'].sum()
        total_logins = df['has_login'].sum()
        
        tab1, tab2 = st.tabs(["💰 PF Tracker", "🏆 RM Leaderboard"])

        with tab1:
            c1, c2 = st.columns(2)
            c1.metric("Total PFs", int(total_pfs))
            c2.metric("Total Logins", int(total_logins))
            
            # Progress Bar
            progress = min(total_pfs / pf_target, 1.0)
            st.write(f"### Target Progress: {progress*100:.1f}%")
            st.progress(progress)
            if progress >= 1.0: st.balloons()

        with tab2:
            st.subheader("🏆 RM Ranking")
            rm_group = df.groupby(rm_col).agg(
                Logins=('has_login', 'sum'),
                PFs=('has_pf', 'sum')
            ).reset_index().sort_values('PFs', ascending=False)
            
            st.dataframe(rm_group.style.background_gradient(cmap='Greens', subset=['PFs']), use_container_width=True)
else:
    st.info("Upload CSV to start.")
