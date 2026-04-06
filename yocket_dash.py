import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from datetime import datetime
import requests
import io

API_KEY = st.secrets.get("GEMINI_API_KEY") 
if API_KEY:
    genai.configure(api_key=API_KEY)

st.title("🛡️ Non Finco Fall 26:  Powered By Gemini")

# --- DUAL-API FETCH ENGINE ---
@st.cache_data(ttl=3600)
def fetch_metabase_report(secret_card_key):
    try:
        mb_url = st.secrets["MB_URL"]
        username = st.secrets["MB_USER"]
        password = st.secrets["MB_PASS"]
        card_id = st.secrets.get(secret_card_key)
        
        if not card_id:
            return None

        session_req = requests.post(f"{mb_url}/api/session", json={"username": username, "password": password})
        session_req.raise_for_status()
        token = session_req.json()["id"]
        
        headers = {"X-Metabase-Session": token}
        csv_req = requests.post(f"{mb_url}/api/card/{card_id}/query/csv", headers=headers)
        csv_req.raise_for_status()
        
        return pd.read_csv(io.StringIO(csv_req.text))
        
    except Exception as e:
        st.error(f"🚨 Failed to pull {secret_card_key} from Metabase: {e}")
        return None

df = None
df_hist = None

with st.sidebar:
    st.header("📊 Controls")
    pf_target = st.number_input("Monthly PF Target", min_value=1, value=50)
    
    st.divider()
    st.markdown("### ⚙️ Data Source")
    use_manual = st.checkbox("Use Manual CSV Upload instead of Live API")
    
    if use_manual:
        uploaded_file = st.file_uploader("Upload LIVE Metabase CSV", type=["csv"])
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
    else:
        with st.spinner("Fetching Live & Historical pipelines from Metabase..."):
            df = fetch_metabase_report("MB_CARD_ID")
            df_hist = fetch_metabase_report("MB_HIST_CARD_ID")
            
            if df is not None:
                hist_len = len(df_hist) if df_hist is not None else 0
                st.success(f"✅ Data Pulled! Live: {len(df)} | History: {hist_len}")

if df is not None: 
    
    l_col, p_col, rm_col = 'Login_Date', 'PF_Date', 'OwnerIdName'
    age_col, lcb_col, admit_col = 'Aging_Days', 'ConnectedDateBucket', 'mx_Admit_recieved'
    stage_col, ltv_col, q_col = 'New_PS', 'CallDateBucket', 'Qualified_Date'
    
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

    for stage, col_name in funnel_date_cols.items():
        if col_name in df.columns:
            df[col_name] = pd.to_datetime(df[col_name], errors='coerce')

    df['has_login'] = df[[l_col, 'Sanction_Date', p_col]].notna().any(axis=1) if l_col in df.columns else False
    df['has_pf'] = df[p_col].notna() if p_col in df.columns else False

    with st.sidebar:
        all_rms = sorted(df[rm_col].dropna().unique()) if rm_col in df.columns else []
        selected_rms = st.multiselect("Select RMs", all_rms, default=all_rms)
        
        if q_col in df.columns:
            min_date = df[q_col].min().to_pydatetime()
            max_date = df[q_col].max().to_pydatetime()
        else:
            min_date, max_date = datetime(2024, 1, 1), datetime.now()
            
        date_range = st.date_input("Qualified Date Range", [min_date, max_date])

    mask = df[rm_col].isin(selected_rms) if rm_col in df.columns else pd.Series(True, index=df.index)
    if len(date_range) == 2 and q_col in df.columns:
        mask = mask & (df[q_col].dt.date >= date_range[0]) & (df[q_col].dt.date <= date_range[1])
    
    f_df = df[mask].copy()

    t_pf = int(f_df['has_pf'].sum())
    t_login = int(f_df['has_login'].sum())
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current PFs", t_pf, delta=f"{t_pf - pf_target}")
    m2.metric("Logins", t_login)
    m3.metric("Conv. %", f"{(t_pf/t_login*100):.1f}%" if t_login > 0 else "0%")
    m4.metric("Pending Target", max(0, pf_target - t_pf))

    tab_funnel, tab_ltb_lcb, tab_ai, tab_leader, tab_priority, tab_ml = st.tabs([
        "📊 Pipeline Funnel", "📞 LTB / LCB Matrix", "✨ AI Audit", "🏆 RM Rankings", "🔥 Hit-List", "🧠 ML Predictor"
    ])

    with tab_funnel:
        st.subheader("Non Finco Overall Funnel")
        funnel_data = []
        for stage_name, date_col in funnel_date_cols.items():
            if date_col in f_df.columns:
                count = f_df[date_col].notna().sum()
                funnel_data.append({'Stage': stage_name, 'Total Reached': count})
        
        if funnel_data:
            funnel_df = pd.DataFrame(funnel_data)
            fig_funnel = px.funnel(funnel_df, x='Total Reached', y='Stage', 
                                   title="Lead Progression Funnel",
                                   color_discrete_sequence=['#5da5da'])
            fig_funnel.update_layout(yaxis_title=None)
            st.plotly_chart(fig_funnel, use_container_width=True)
            st.dataframe(funnel_df, use_container_width=True, hide_index=True)

    with tab_ltb_lcb:
        st.subheader("📞 Targeted Call & Connection Matrices")
        
        pre_login_stages = ['Qualified', 'App Not Started', 'App Start', 'Ready To Share', 'Bank Prospect']
        post_login_stages = ['Login', 'Sanction']
        
        def classify_stage(stage_val):
            val = str(stage_val).lower()
            if any(s.lower() in val for s in pre_login_stages): return 'Pre-Login'
            if any(s.lower() in val for s in post_login_stages): return 'Post-Login'
            return 'Exclude'
            
        if stage_col in f_df.columns:
            f_df['Matrix_Group'] = f_df[stage_col].apply(classify_stage)
            pre_df = f_df[f_df['Matrix_Group'] == 'Pre-Login']
            post_df = f_df[f_df['Matrix_Group'] == 'Post-Login']
        else:
            pre_df, post_df = pd.DataFrame(), pd.DataFrame()

        def draw_matrix(data, rm_column, bucket_column, cmap_color):
            if data.empty or bucket_column not in data.columns: return
            pivot = pd.crosstab(data[rm_column], data[bucket_column], margins=True, margins_name='OVERALL')
            bucket_order = ['A 0-3 Days', 'B 4-7 Days', 'C 8-11 Days', 'D 12-15 Days', 'E More than 15 Days', 'Not Connected']
            cols = [c for c in bucket_order if c in pivot.columns] + [c for c in pivot.columns if c not in bucket_order and c != 'OVERALL'] + (['OVERALL'] if 'OVERALL' in pivot.columns else [])
            pivot = pivot.reindex(columns=list(dict.fromkeys(cols)))
            if 'OVERALL' in pivot.columns: pivot = pivot.sort_values(by='OVERALL', ascending=False)
            st.dataframe(pivot.style.background_gradient(cmap=cmap_color, axis=None), use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🏃‍♂️ Pre-Login (Building the App)")
            draw_matrix(pre_df, rm_col, ltv_col, 'Blues')
        with col2:
            st.markdown("#### 📝 Post-Login (Chasing Sanction)")
            draw_matrix(post_df, rm_col, ltv_col, 'Blues')

        st.divider()
        col3, col4 = st.columns(2)
        with col3:
            st.markdown("#### 🏃‍♂️ Pre-Login Connections")
            draw_matrix(pre_df, rm_col, lcb_col, 'Purples')
        with col4:
            st.markdown("#### 📝 Post-Login Connections")
            draw_matrix(post_df, rm_col, lcb_col, 'Purples')

    with tab_ai:
        st.subheader("🕵️ AI Diagnostic & Strategy")
        if st.button("🚀 Run Performance Audit"):
            if not API_KEY:
                st.error("Please add GEMINI_API_KEY to Streamlit Secrets.")
            else:
                with st.spinner("Analyzing..."):
                    try:
                        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        best_model = next((m for m in available if '3.1-flash' in m), next((m for m in available if '3-flash' in m), available[0] if available else None))
                        if best_model:
                            model = genai.GenerativeModel(best_model)
                            rm_stats = f_df.groupby(rm_col).agg({'has_pf': 'sum', 'has_login': 'sum', age_col: 'mean'}).to_string()
                            prompt = f"Act as a Business Analyst. Target is {pf_target} PFs. Analyze these RMs: {rm_stats}. Give 3 tips."
                            response = model.generate_content(prompt)
                            st.markdown(response.text)
                    except Exception as e:
                        st.error(f"🤖 AI Error: {e}")

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

  # ==========================================
    # TAB 6: THE SLA ENFORCER ENGINE
    # ==========================================
    with tab_ml:
        st.subheader("🎯 The 9:00 AM SLA Enforcer")
        st.write("Strict deterministic logic based on Follow-Ups, Golden Path to Login, and RM Connection SLAs.")
        
        # --- NEW COLUMN DEFINITION ---
        # MAKE SURE THIS MATCHES YOUR METABASE COLUMN EXACTLY
        follow_up_col = 'Follow_Up_Date' 
        
        if df_hist is None and use_manual:
            st.info("Upload historical data to calculate the Golden Path to Login.")
            hist_file = st.file_uploader("📂 Upload Historical CSV", type=['csv'])
            if hist_file is not None:
                df_hist = pd.read_csv(hist_file)

        if df_hist is not None:
            with st.spinner("Enforcing Pipeline SLAs..."):
                try:
                    # --- 1. THE GOLDEN PATH (Goal = LOGIN) ---
                    # We consider Login, Sanction, or PF as a "Win" for this calculation
                    success_stages = ['login', 'sanction', 'pf']
                    df_hist['Reached_Login'] = df_hist[stage_col].astype(str).str.lower().apply(lambda x: any(s in x for s in success_stages))
                    
                    winners_df = df_hist[df_hist['Reached_Login']].copy()
                    
                    if len(winners_df) < 5:
                        st.warning("Not enough historical 'Logins' to calculate a reliable baseline.")
                    else:
                        winners_df[age_col] = pd.to_numeric(winners_df[age_col], errors='coerce').fillna(0)
                        
                        # Calculate Golden Path (Median Days per Stage)
                        golden_path = winners_df.groupby([stage_col])[age_col].median().reset_index()
                        golden_path.rename(columns={age_col: 'Target_Pace_Days'}, inplace=True)
                        golden_path['Target_Pace_Days'] = golden_path['Target_Pace_Days'].round(0).astype(int)

                        # --- 2. LIVE PIPELINE PREP ---
                        # Filter out already PF'd or Lost leads
                        live_pipeline = f_df[(~f_df['has_pf']) & (~f_df[stage_col].astype(str).str.lower().str.contains('lost', na=False))].copy()
                        live_pipeline[age_col] = pd.to_numeric(live_pipeline[age_col], errors='coerce').fillna(0)
                        
                        action_df = pd.merge(live_pipeline, golden_path, on=[stage_col], how='left')
                        action_df['Target_Pace_Days'] = action_df['Target_Pace_Days'].fillna(5) # Default to 5 if unknown
                        action_df['Lag_Variance'] = action_df[age_col] - action_df['Target_Pace_Days']

                        # Clean up Follow-up Dates for accurate "Today" comparison
                        today = pd.to_datetime('today').normalize()
                        if follow_up_col in action_df.columns:
                            action_df[follow_up_col] = pd.to_datetime(action_df[follow_up_col], errors='coerce').dt.normalize()
                        else:
                            action_df[follow_up_col] = pd.NaT

                        # --- 3. THE STRICT SLA LOGIC (Your Brain Dump) ---
                        def enforce_sla(row):
                            # Rule 1: Absolute Override - Follow Up is Today (or overdue)
                            f_date = row.get(follow_up_col)
                            if pd.notna(f_date) and f_date <= today:
                                return "🔴 CRITICAL (Follow-Up Due)"
                                
                            # Prepare variables for Rule 2 & 3
                            lag = row.get('Lag_Variance', 0)
                            lcb = str(row.get(lcb_col, '')).lower()
                            
                            # Rule 2: Golden Aging Check
                            if lag > 0:
                                # Rule 3: The SLA Forgiveness Check
                                if '0-3' in lcb:
                                    return "🟢 SAFE (Delayed but Engaged)"
                                else:
                                    return "🔴 CRITICAL (Stagnant & Ignored)"
                            
                            # Default
                            return "🟢 SAFE (On Pace)"

                        action_df['Action_Required'] = action_df.apply(enforce_sla, axis=1)
                        
                        # Create a sorting score to push Criticals to the top, ordered by Lag severity
                        action_df['Sort_Score'] = action_df.apply(lambda x: 1000 + x['Lag_Variance'] if 'CRITICAL' in x['Action_Required'] else x['Lag_Variance'], axis=1)

                        # --- UI: RM ACCOUNTABILITY ---
                        st.markdown("### 👥 RM Accountability Matrix")
                        st.caption("RMs are flagged strictly if a lead has a Follow-up today, OR if it is overdue and they haven't spoken to them in 3+ days.")
                        
                        rm_summary = action_df.groupby(rm_col).agg(
                            Active_Leads=(rm_col, 'count'),
                            Critical_Violations=('Action_Required', lambda x: (x.str.contains('CRITICAL')).sum()),
                            Safe_Leads=('Action_Required', lambda x: (x.str.contains('SAFE')).sum())
                        ).sort_values('Critical_Violations', ascending=False)
                        
                        st.dataframe(rm_summary.style.background_gradient(cmap='Reds', subset=['Critical_Violations']), use_container_width=True)

                        st.divider()

                        # --- UI: THE 9:00 AM HIT-LIST ---
                        st.markdown("### 🚨 The 9:00 AM Master Hit-List (Critical SLA Violations)")
                        st.caption("These leads broke the rules. Scroll right to see full details.")
                        
                        # Filter ONLY Critical leads
                        hit_list = action_df[action_df['Action_Required'].str.contains('CRITICAL')].copy()
                        hit_list = hit_list.sort_values(['Sort_Score'], ascending=[False])
                        
                        if hit_list.empty:
                            st.success("🎉 Flawless execution! 0 Critical Leads today.")
                        else:
                            # Put the Hero columns first, then dump all original data
                            hero_cols = ['Action_Required', rm_col, stage_col, age_col, 'Lag_Variance', lcb_col, follow_up_col]
                            hero_cols = [c for c in hero_cols if c in hit_list.columns]
                            
                            ignore_cols = hero_cols + ['Target_Pace_Days', 'Reached_Login', 'Sort_Score']
                            original_cols = [c for c in hit_list.columns if c not in ignore_cols]
                            
                            display_cols = hero_cols + original_cols
                            
                            # Custom styling to make the Action column pop
                            def style_action(val):
                                color = '#ffebee' if 'CRITICAL' in str(val) else ''
                                return f'background-color: {color}'
                                
                            styled_df = hit_list[display_cols].style.map(style_action, subset=['Action_Required'])
                            st.dataframe(styled_df, use_container_width=True, hide_index=True)

                except Exception as e:
                    st.error(f"🚨 Engine Failed: {e}")
        else:
            if not use_manual:
                st.info("Waiting for historical data feed from Metabase...")
else:
    st.info("👋 Welcome! Please upload your Metabase CSV in the sidebar to begin.")
