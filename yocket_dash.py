import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from datetime import datetime

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="Yocket DataSight Pro", layout="wide")

# --- 2. AI SETUP ---
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
    
    # Date Columns from your Metabase (used for the Funnel)
    funnel_date_cols = {
        'Qualified': 'Qualified_Date',
        'App Not Started': 'App_Not_Started_Date',
        'App Start': 'App_Start_Date',
        'Ready To Share': 'RTS_Date',
        'Bank Prospect': 'Bank_Prospect_Date',
        'Login': 'Login_Date',
        'Sanction': 'Sanction_Date',
        'PF': 'PF_Date'
    }

    # Convert known dates
    for stage, col_name in funnel_date_cols.items():
        if col_name in df.columns:
            df[col_name] = pd.to_datetime(df[col_name], errors='coerce')

    df['has_login'] = df[[l_col, 'Sanction_Date', p_col]].notna().any(axis=1) if l_col in df.columns else False
    df['has_pf'] = df[p_col].notna() if p_col in df.columns else False

    # --- SIDEBAR FILTER LOGIC ---
    with st.sidebar:
        all_rms = sorted(df[rm_col].dropna().unique()) if rm_col in df.columns else []
        selected_rms = st.multiselect("Select RMs", all_rms, default=all_rms)
        
        if q_col in df.columns:
            min_date = df[q_col].min().to_pydatetime()
            max_date = df[q_col].max().to_pydatetime()
        else:
            min_date, max_date = datetime(2024, 1, 1), datetime.now()
            
        date_range = st.date_input("Qualified Date Range", [min_date, max_date])

    # Apply Filters
    mask = df[rm_col].isin(selected_rms) if rm_col in df.columns else pd.Series(True, index=df.index)
    if len(date_range) == 2 and q_col in df.columns:
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
    tab_funnel, tab_ltb_lcb, tab_ai, tab_leader, tab_priority = st.tabs([
        "📊 Pipeline Funnel", "📞 LTB / LCB Matrix", "✨ AI Audit", "🏆 RM Rankings", "🔥 Hit-List"
    ])

    # ==========================================
    # TAB 1: OVERALL FUNNEL (Like Image 1)
    # ==========================================
    with tab_funnel:
        st.subheader("Non Finco Overall Funnel")
        
        # Calculate 'Total Reached' for each stage based on Date presence
        funnel_data = []
        for stage_name, date_col in funnel_date_cols.items():
            if date_col in f_df.columns:
                # Count how many leads have a date stamp for this stage
                count = f_df[date_col].notna().sum()
                funnel_data.append({'Stage': stage_name, 'Total Reached': count})
        
        if funnel_data:
            funnel_df = pd.DataFrame(funnel_data)
            
            # Draw the Plotly Funnel
            fig_funnel = px.funnel(funnel_df, x='Total Reached', y='Stage', 
                                   title="Lead Progression Funnel",
                                   color_discrete_sequence=['#5da5da']) # Leap Finance Blue
            fig_funnel.update_layout(yaxis_title=None)
            st.plotly_chart(fig_funnel, use_container_width=True)
            
            # Show the Data Table below it
            st.write("#### Funnel Data Breakdown")
            st.dataframe(funnel_df, use_container_width=True, hide_index=True)
        else:
            st.info("Missing date columns required to build the Funnel.")

    # ==========================================
    # TAB 2: LTB / LCB MATRIX (Like Images 2 & 3)
    # ==========================================
    with tab_ltb_lcb:
        st.subheader("RM Wise Call & Connection Buckets")
        
        # Define the ideal order for buckets so they sort nicely
        bucket_order = ['A 0-3 Days', 'B 4-7 Days', 'C 8-11 Days', 'D 12-15 Days', 'E More than 15 Days']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### LTB (Last Touched/Called Bucket)")
            if ltv_col in f_df.columns and rm_col in f_df.columns:
                # Create Pivot Table
                ltb_pivot = pd.crosstab(f_df[rm_col], f_df[ltv_col], margins=True, margins_name='OVERALL')
                
                # Sort columns if they exist in our predefined list
                cols = [c for c in bucket_order if c in ltb_pivot.columns] + [c for c in ltb_pivot.columns if c not in bucket_order and c != 'OVERALL'] + ['OVERALL']
                # Don't duplicate OVERALL
                cols = list(dict.fromkeys(cols)) 
                
                ltb_pivot = ltb_pivot.reindex(columns=[c for c in cols if c in ltb_pivot.columns])
                
                # Sort rows by OVERALL volume
                ltb_pivot = ltb_pivot.sort_values(by='OVERALL', ascending=False)
                st.dataframe(ltb_pivot.style.background_gradient(cmap='Blues', axis=None), use_container_width=True)
            else:
                st.info("CallDateBucket missing from data.")

        with col2:
            st.markdown("#### LCB (Last Connected Bucket)")
            if lcb_col in f_df.columns and rm_col in f_df.columns:
                # Create Pivot Table
                lcb_pivot = pd.crosstab(f_df[rm_col], f_df[lcb_col], margins=True, margins_name='OVERALL')
                
                # Sort columns
                cols = [c for c in bucket_order if c in lcb_pivot.columns] + [c for c in lcb_pivot.columns if c not in bucket_order and c != 'OVERALL'] + ['OVERALL']
                cols = list(dict.fromkeys(cols))
                
                lcb_pivot = lcb_pivot.reindex(columns=[c for c in cols if c in lcb_pivot.columns])
                
                # Sort rows by OVERALL volume
                lcb_pivot = lcb_pivot.sort_values(by='OVERALL', ascending=False)
                st.dataframe(lcb_pivot.style.background_gradient(cmap='Purples', axis=None), use_container_width=True)
            else:
                st.info("ConnectedDateBucket missing from data.")

    # ==========================================
    # TAB 3: AI STRATEGY
    # ==========================================
    with tab_ai:
        st.subheader("🕵️ AI Diagnostic & Strategy")
        if st.button("🚀 Run Performance Audit"):
            if not API_KEY:
                st.error("Please add GEMINI_API_KEY to Streamlit Secrets.")
            else:
                with st.spinner("Finding the best available model..."):
                    try:
                        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        
                        best_model = None
                        for target in ['3.1-flash', '3-flash', '1.5-flash']:
                            match = next((m for m in available if target in m), None)
                            if match:
                                best_model = match
                                break
                        
                        best_model = best_model or (available[0] if available else None)

                        if not best_model:
                            st.error("No compatible models found for this API key.")
                        else:
                            model = genai.GenerativeModel(best_model)
                            rm_stats = f_df.groupby(rm_col).agg({'has_pf': 'sum', 'has_login': 'sum', age_col: 'mean'}).to_string()
                            prompt = f"Act as a Business Analyst. Target is {pf_target} PFs. Analyze these RMs: {rm_stats}. Give 3 tips."
                            response = model.generate_content(prompt)
                            st.markdown(response.text)
                    except Exception as e:
                        st.error(f"🤖 AI Error: {e}")

    # ==========================================
    # TAB 4: RM RANKINGS & TAB 5: PRIORITY HIT-LIST 
    # ==========================================
    with tab_leader:
        lb = f_df.groupby(rm_col).agg(PFs=('has_pf','sum'), Logins=('has_login','sum')).sort_values('PFs', ascending=False)
        st.dataframe(lb.style.background_gradient(cmap='Greens', subset=['PFs']), use_container_width=True)

    with tab_priority:
        active = f_df[~f_df['has_pf']].copy()
        active['Score'] = 0
        if stage_col in active.columns:
            active.loc[active[stage_col] == 'G. Sanction', 'Score'] += 50
            active.loc[active[stage_col] == 'F. Login', 'Score'] += 20
        if admit_col in active.columns:
            active.loc[active[admit_col].str.contains('Admit', na=False), 'Score'] += 30
        
        hit_list = active.sort_values('Score', ascending=False).head(25)
        st.dataframe(hit_list[['Score', rm_col, stage_col, 'Phone', 'LSQ_link']].style.background_gradient(cmap='Oranges', subset=['Score']), use_container_width=True, hide_index=True)

else:
    st.info("👋 Welcome! Please upload your Metabase CSV in the sidebar to begin.")
