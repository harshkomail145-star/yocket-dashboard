import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai

# --- PAGE CONFIG & THEME ---
st.set_page_config(page_title="Yocket DataSight", layout="wide")

# Custom CSS to mimic the AI Studio "Zinc/Indigo" look
st.markdown("""
    <style>
    .main { background-color: #fafaFA; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e4e4e7; shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05); }
    div.stButton > button:first-child { background-color: #4f46e5; color: white; border-radius: 8px; border: none; padding: 10px 24px; }
    div.stButton > button:hover { background-color: #4338ca; border: none; }
    h1, h2, h3 { color: #18181b; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- AI SETUP ---
# Replace with your actual key or use streamlit secrets
genai.configure(api_key=st.secrets.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE"))

# --- APP HEADER ---
st.title("🛡️ Yocket Finance: DataSight")
st.markdown("Automated Lead Audit & AI-Powered RM Strategy")
st.divider()

# --- SIDEBAR ---
with st.sidebar:
    st.header("📤 Data Control")
    uploaded_file = st.file_uploader("Upload Metabase CSV", type=["csv"])
    pf_target = st.number_input("Monthly PF Target", min_value=1, value=50)
    st.divider()
    st.info("The AI engine uses Gemini 1.5 Flash to analyze RM performance.")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # --- DATA ENGINE (Refined Logic) ---
    l_col, p_col, rm_col = 'Login_Date', 'PF_Date', 'OwnerIdName'
    age_col, lcb_col = 'Aging_Days', 'ConnectedDateBucket'
    
    # Convert dates
    for c in [l_col, p_col, 'Qualified_Date']:
        if c in df.columns: df[c] = pd.to_datetime(df[c], errors='coerce')

    df['has_login'] = df[[l_col, 'Sanction_Date', p_col]].notna().any(axis=1) if l_col in df.columns else False
    df['has_pf'] = df[p_col].notna() if p_col in df.columns else False
    
    # --- EXECUTIVE METRICS ---
    t_pf = int(df['has_pf'].sum())
    t_login = int(df['has_login'].sum())
    conv = (t_pf / t_login * 100) if t_login > 0 else 0
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total PFs", t_pf)
    m2.metric("Total Logins", t_login)
    m3.metric("Login ➡️ PF %", f"{conv:.1f}%")
    m4.metric("Target Gap", max(0, pf_target - t_pf))

    # --- TABS ---
    tab_ai, tab_leaderboard, tab_lag = st.tabs(["✨ AI Business Insights", "🏆 RM Leaderboard", "🚨 Lag Analysis"])

    # ==========================================
    # TAB 1: THE AI STUDIO "MAGIC" BUTTON
    # ==========================================
    with tab_ai:
        st.subheader("AI Strategy Engine")
        st.write("Generate an automated audit based on current RM performance data.")
        
        if st.button("Generate AI Insights"):
            with st.spinner("AI is analyzing RM performance..."):
                # Prepare a summary for Gemini (Don't send raw PII)
                rm_summary = df.groupby(rm_col).agg({
                    'has_pf': 'sum',
                    'has_login': 'sum',
                    'Aging_Days': 'mean'
                }).reset_index().to_string()

                prompt = f"""
                You are an expert Business Analyst for an education loan company. 
                Our target is PF (Processing Fee) Paid.
                Here is the RM Performance Data:
                {rm_summary}
                
                Please provide:
                1. **Executive Summary**: Which RMs are leading and who is lagging.
                2. **The Problem Zone**: Identify RMs with high logins but low PFs.
                3. **Action Plan**: 3 specific coaching tips for the team to hit the target of {pf_target} PFs.
                """
                
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                
                st.markdown("---")
                st.markdown(response.text)

    # ==========================================
    # TAB 2: LEADERBOARD
    # ==========================================
    with tab_leaderboard:
        rm_perf = df.groupby(rm_col).agg(Logins=('has_login','sum'), PFs=('has_pf','sum')).reset_index()
        rm_perf = rm_perf.sort_values('PFs', ascending=False)
        
        st.dataframe(rm_perf.style.background_gradient(cmap='Greens', subset=['PFs']), use_container_width=True)

    # ==========================================
    # TAB 3: LAG ANALYSIS
    # ==========================================
    with tab_lag:
        risk_buckets = ['E More than 15 Days', 'Not Connected']
        df['is_ghosted'] = df[lcb_col].isin(risk_buckets)
        
        rm_lag = df.groupby(rm_col).agg(
            Ghosted_Leads=('is_ghosted', 'sum'),
            Avg_Age=(age_col, 'mean')
        ).reset_index().sort_values('Ghosted_Leads', ascending=False)
        
        st.write("### 🚨 High Risk RMs (Ghosting >15 Days)")
        st.dataframe(rm_lag.style.background_gradient(cmap='Reds', subset=['Ghosted_Leads']), use_container_width=True)

else:
    st.info("👋 Systems Ready. Please upload Yocket Metabase data in the sidebar.")
