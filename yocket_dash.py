import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai

# --- PAGE CONFIG & THEME ---
st.set_page_config(page_title="Yocket DataSight", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #fafaFA; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e4e4e7; border-left: 5px solid #4f46e5; }
    div.stButton > button:first-child { background-color: #4f46e5; color: white; border-radius: 8px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- AI SETUP ---
genai.configure(api_key=st.secrets.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE"))

st.title("🛡️ Yocket Finance: DataSight")
st.markdown("### Automated Lead Audit & Priority Calling")

uploaded_file = st.sidebar.file_uploader("Upload Metabase CSV", type=["csv"])
pf_target = st.sidebar.number_input("Monthly PF Target", min_value=1, value=50)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # --- DATA ENGINE ---
    l_col, p_col, rm_col = 'Login_Date', 'PF_Date', 'OwnerIdName'
    age_col, lcb_col, admit_col = 'Aging_Days', 'ConnectedDateBucket', 'mx_Admit_recieved'
    stage_col, ltv_col = 'New_PS', 'CallDateBucket'
    
    for c in [l_col, p_col, 'Qualified_Date']:
        if c in df.columns: df[c] = pd.to_datetime(df[c], errors='coerce')

    df['has_login'] = df[[l_col, 'Sanction_Date', p_col]].notna().any(axis=1) if l_col in df.columns else False
    df['has_pf'] = df[p_col].notna() if p_col in df.columns else False
    
    # --- METRICS ---
    t_pf = int(df['has_pf'].sum())
    t_login = int(df['has_login'].sum())
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total PFs", t_pf)
    m2.metric("Total Logins", t_login)
    m3.metric("Conv. %", f"{(t_pf/t_login*100):.1f}%" if t_login > 0 else "0%")
    m4.metric("Target Gap", max(0, pf_target - t_pf))

    # --- TABS ---
    tab_ai, tab_leader, tab_lag, tab_priority = st.tabs(["✨ AI Insights", "🏆 RM Leaderboard", "🚨 Lag Analysis", "📞 Priority Hit-List"])

    with tab_ai:
        if st.button("Generate AI Strategy"):
            model = genai.GenerativeModel('gemini-1.5-flash')
            rm_summary = df.groupby(rm_col).agg({'has_pf': 'sum', 'has_login': 'sum', 'Aging_Days': 'mean'}).to_string()
            response = model.generate_content(f"Analyze this RM data and provide a strategy to hit {pf_target} PFs: {rm_summary}")
            st.markdown(response.text)

    with tab_leader:
        st.dataframe(df.groupby(rm_col).agg(PFs=('has_pf','sum')).sort_values('PFs', ascending=False), use_container_width=True)

    with tab_lag:
        risk_buckets = ['E More than 15 Days', 'Not Connected']
        df['is_ghosted'] = df[lcb_col].isin(risk_buckets) if lcb_col in df.columns else False
        st.dataframe(df.groupby(rm_col).agg(Ghosted_Leads=('is_ghosted','sum')).sort_values('Ghosted_Leads', ascending=False), use_container_width=True)

    # ==========================================
    # TAB 4: FIXED PRIORITY HIT-LIST
    # ==========================================
    with tab_priority:
        st.subheader("🔥 High-Probability Leads (Call These First!)")
        
        # Filter for leads that ARE NOT PF YET
        active_leads = df[~df['has_pf']].copy()
        
        # Scoring Logic (Numeric)
        active_leads['Priority_Score'] = 0
        if stage_col in active_leads.columns:
            active_leads.loc[active_leads[stage_col] == 'G. Sanction', 'Priority_Score'] += 50
            active_leads.loc[active_leads[stage_col] == 'F. Login', 'Priority_Score'] += 30
        if admit_col in active_leads.columns:
            active_leads.loc[active_leads[admit_col] == 'Admitted', 'Priority_Score'] += 20
        if ltv_col in active_leads.columns:
            active_leads.loc[active_leads[ltv_col] == 'A 0-3 Days', 'Priority_Score'] -= 15
        
        hit_list = active_leads.sort_values('Priority_Score', ascending=False).head(20)
        
        # Fixed Display: Only apply gradient to the NUMERIC 'Priority_Score' column
        display_cols = ['Priority_Score', rm_col, stage_col, admit_col, lcb_col, 'Phone', 'LSQ_link']
        
        st.dataframe(
            hit_list[display_cols].style.background_gradient(cmap='Blues', subset=['Priority_Score']),
            use_container_width=True,
            hide_index=True
        )
        
        st.success("💡 **BA Insight:** RMs should focus on the top-ranked leads above. A higher score means the lead is closer to the PF stage.")

else:
    st.info("Upload CSV to generate the Priority Hit-List.")
