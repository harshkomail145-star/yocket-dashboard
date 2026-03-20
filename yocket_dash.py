import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Yocket PF Tracker", layout="wide")
st.title("🎯 Yocket Finance: PF & Login Command Center")

uploaded_file = st.sidebar.file_uploader("Upload Metabase CSV", type=["csv"])
pf_target = st.sidebar.number_input("Monthly PF Target", min_value=1, value=50)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # --- EXACT COLUMN MAPPING BASED ON YOUR EXPORT ---
    q_col = 'Qualified_Date'
    l_col = 'Login_Date'
    s_col = 'Sanction_Date'
    p_col = 'PF_Date'   # Matched to your list!
    rm_col = 'OwnerIdName' # Matched to your list!
    
    # Check if they exist to prevent crashing
    if p_col in df.columns and l_col in df.columns and rm_col in df.columns:
        
        # Convert to datetime
        for c in [q_col, l_col, s_col, p_col]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors='coerce')

        # --- JOURNEY LOGIC ---
        # Lead hit Login if it has a Login date OR any later date (Sanction or PF)
        # Note: We don't have Disbursed_Date in your list, so we use what we have.
        df['has_login'] = df[[l_col, s_col, p_col]].notna().any(axis=1)
        
        # Lead hit PF if it has a PF date
        df['has_pf'] = df[p_col].notna()

        # --- DASHBOARD UI ---
        total_pfs = df['has_pf'].sum()
        total_logins = df['has_login'].sum()
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Total PFs", int(total_pfs))
        col_m2.metric("Total Logins", int(total_logins))
        col_m3.metric("Conv. Rate %", f"{(total_pfs/total_logins*100):.1f}%" if total_logins > 0 else "0%")

        st.divider()

        tab1, tab2 = st.tabs(["📊 Performance Charts", "🏆 RM Leaderboard"])

        with tab1:
            # Progress Bar
            progress = min(total_pfs / pf_target, 1.0)
            st.write(f"### PF Target Progress: {progress*100:.1f}%")
            st.progress(progress)
            if progress >= 1.0: st.balloons()
            
            # Simple Funnel
            funnel_df = pd.DataFrame({
                'Stage': ['Qualified', 'Login', 'PF'],
                'Count': [df[q_col].notna().sum(), total_logins, total_pfs]
            })
            fig = px.funnel(funnel_df, x='Count', y='Stage', title="Team Conversion Funnel")
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.subheader("🏆 RM Ranking (Based on PF Dates)")
            rm_group = df.groupby(rm_col).agg(
                Qualified=(q_col, 'count'),
                Logins=('has_login', 'sum'),
                PFs=('has_pf', 'sum')
            ).reset_index()
            
            # Calculate RM level conversion
            rm_group['Login_to_PF_%'] = (rm_group['PFs'] / rm_group['Logins'] * 100).fillna(0).round(1)
            rm_group = rm_group.sort_values('PFs', ascending=False)
            
            st.dataframe(
                rm_group.style.background_gradient(cmap='YlGn', subset=['PFs', 'Login_to_PF_%']),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.error(f"⚠️ Still missing columns. Please check if {l_col}, {p_col}, and {rm_col} are in your CSV.")

else:
    st.info("Upload the Metabase CSV to see the PF Leaderboard.")
