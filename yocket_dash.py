import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from datetime import datetime

# --- 1. PAGE CONFIG & THEME (Must be at the top) ---
st.set_page_config(page_title="Yocket DataSight Pro", layout="wide")

# --- 2. AI SETUP (Moved after imports) ---
API_KEY = st.secrets.get("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.sidebar.warning("⚠️ Gemini API Key not found in Streamlit Secrets!")

# --- 3. CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; border-top: 4px solid #4f46e5; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 8px 8px 0 0; padding: 8px 16px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Yocket Finance: DataSight Pro")

# --- 4. SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("📊 Controls")
    uploaded_file = st.file_uploader("Upload Metabase CSV", type=["csv"])
    pf_target = st.number_input("Monthly PF Target", min_value=1, value=50)
    
    st.divider()
    st.markdown("### 🔍 Global Filters")

# --- 5. MAIN LOGIC ---
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # --- DATA ENGINE ---
    l_col, p_col, rm_col = 'Login_Date', 'PF_Date', 'OwnerIdName'
    age_col, lcb_col, admit_col = 'Aging_Days', 'ConnectedDateBucket', 'mx_Admit_recieved'
    stage_col, ltv_col, q_col = 'New_PS', 'CallDateBucket', 'Qualified_Date'
    
    for c in [l_col, p_col, q_col]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors='coerce')

    df['has_login'] = df[[l_col, 'Sanction_Date', p_col]].notna().any(axis=1) if l_col in df.columns else False
    df['has_pf'] = df[p_col].notna() if p_col in df.columns else False

    # --- SIDEBAR FILTER LOGIC ---
    with st.sidebar:
        all_rms = sorted(df[rm_col].dropna().unique())
        selected_rms = st.multiselect("Select RMs", all_rms, default=all_rms)
        
        min_date = df[q_col].min().to_pydatetime() if q_col in df.columns else datetime(2024, 1, 1)
        max_date = df[q_col].max().to_pydatetime() if q_col in df.columns else datetime.now()
        date_range = st.date_input("Qualified Date Range", [min_date, max_date])

    mask = df[rm_col].isin(selected_rms)
    if len(date_range) == 2:
        mask = mask & (df[q_col].dt.date >= date_range[0]) & (df[q_col].dt.date <= date_range[1])
    
    f_df = df[mask].copy()

    # --- TOP LEVEL METRICS ---
    t_pf = int(f_df['has_pf'].sum())
    t_login = int(f_df['has_login'].sum())
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current PFs", t_pf, delta=f"{t_pf - pf_target}")
    m2.metric("Logins", t_login)
    m3.metric("Conv. %", f"{(t_pf/t_login*100):.1f}%" if t_login > 0 else "0%")
    m4.metric("Pending Target", max(0, pf_target - t_pf))

    # --- TABS ---
    tab_trend, tab_ai, tab_leader, tab_priority = st.tabs(["📉 Trends", "✨ AI Audit", "🏆 RM Rankings", "📞 Hit-List"])

    with tab_trend:
        st.subheader("PF Collection Trend")
        if p_col in f_df.columns:
            trend_data = f_df[f_df['has_pf']].groupby(f_df[p_col].dt.date).size().reset_index(name='PF_Count')
            fig = px.line(trend_data, x=p_col, y='PF_Count', title="PFs Collected per Day", markers=True)
            fig.update_traces(line_color='#4f46e5')
            st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # TAB: AI STRATEGY (Improved with Model Fallback)
    # ==========================================
    # ==========================================
    # TAB: AI STRATEGY (Gemini 3.1 Edition)
    # ==========================================
    # ==========================================
    # TAB: AI STRATEGY (Diagnostic Mode)
    # ==========================================
    with tab_ai:
        st.subheader("🕵️ AI Diagnostic & Strategy")
        
        # This button will tell us exactly what your key can see
        if st.button("🔍 Step 1: List Available Models"):
            try:
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                st.write("### Your API Key can see these models:")
                for m in models:
                    st.code(m)
                st.info("Copy the one you want to use and we can hardcode it!")
            except Exception as e:
                st.error(f"Could not list models: {e}")

        st.divider()

        if st.button("🚀 Step 2: Run Performance Audit"):
            if not API_KEY:
                st.error("Please add GEMINI_API_KEY to Streamlit Secrets.")
            else:
                with st.spinner("Finding the best available model..."):
                    try:
                        # --- THE AUTO-PICKER ---
                        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        
                        # We try to find 3.1, then 3.0, then 1.5
                        best_model = None
                        for target in ['3.1-flash', '3-flash', '1.5-flash']:
                            match = next((m for m in available if target in m), None)
                            if match:
                                best_model = match
                                break
                        
                        if not best_model:
                            best_model = available[0] if available else None

                        if not best_model:
                            st.error("No compatible models found for this API key.")
                        else:
                            st.caption(f"Connected to: `{best_model}`")
                            model = genai.GenerativeModel(best_model)

                            # Prepare Data
                            rm_stats = f_df.groupby(rm_col).agg({'has_pf': 'sum', 'has_login': 'sum', age_col: 'mean'}).to_string()
                            prompt = f"Act as a Business Analyst. Target is {pf_target} PFs. Analyze these RMs: {rm_stats}. Give 3 tips."

                            response = model.generate_content(prompt)
                            st.markdown("---")
                            st.markdown(response.text)

                    except Exception as e:
                        st.error(f"🤖 AI Error: {e}")
    with tab_leader:
        col_l, col_r = st.columns(2)
        with col_l:
            st.subheader("Leaderboard (PFs)")
            lb = f_df.groupby(rm_col).agg(PFs=('has_pf','sum'), Logins=('has_login','sum')).sort_values('PFs', ascending=False)
            st.dataframe(lb.style.background_gradient(cmap='Greens', subset=['PFs']), use_container_width=True)
        with col_r:
            st.subheader("🚨 Risk: High Aging Leads")
            risk = f_df[f_df[age_col] > 15].groupby(rm_col).size().reset_index(name='Stagnant_Leads').sort_values('Stagnant_Leads', ascending=False)
            st.dataframe(risk.style.background_gradient(cmap='Reds'), use_container_width=True)

    with tab_priority:
        active = f_df[~f_df['has_pf']].copy()
        active['Score'] = 0
        if stage_col in active.columns:
            active.loc[active[stage_col] == 'G. Sanction', 'Score'] += 50
            active.loc[active[stage_col] == 'F. Login', 'Score'] += 20
        if admit_col in active.columns:
            active.loc[active[admit_col].str.contains('Admit', na=False), 'Score'] += 30
        
        hit_list = active.sort_values('Score', ascending=False).head(25)
        st.subheader(f"🔥 Top {len(hit_list)} Priority Leads")
        st.dataframe(hit_list[['Score', rm_col, stage_col, 'Phone', 'LSQ_link']].style.background_gradient(cmap='Blues', subset=['Score']), use_container_width=True, hide_index=True)
        
        csv = hit_list.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Hit-List for RMs", data=csv, file_name=f"Priority_Leads_{datetime.now().strftime('%Y%m%d')}.csv", mime='text/csv')

else:
    st.info("👋 Welcome! Please upload your Metabase CSV in the sidebar to begin.")
