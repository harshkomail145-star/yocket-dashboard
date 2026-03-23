import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from datetime import datetime

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="Yocket Bank Meetings", layout="wide")

# --- 2. AI SETUP ---
API_KEY = st.secrets.get("GEMINI_API_KEY") if hasattr(st, "secrets") else None
if API_KEY:
    genai.configure(api_key=API_KEY)

# --- 3. CUSTOM CSS (SaaS Look) ---
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; border-top: 4px solid #4f46e5; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 8px 8px 0 0; padding: 8px 16px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏦 Yocket Bank Meetings Command Center")

# --- 4. SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("📊 Controls")
    uploaded_file = st.file_uploader("Upload Bank Meetings CSV", type=["csv"])
    pf_target = st.number_input("Monthly PF Target", min_value=1, value=50)
    st.divider()
    st.markdown("### 🔍 Global Filters")

# --- MAIN LOGIC ---
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # --- DATA ENGINE MAPPINGS (Tailored to your new CSV) ---
    q_col, l_col, s_col, p_col = 'date_shared', 'login_date', 'sanction_date', 'pf_date'
    rm_col = 'primary_finance_advisor'
    bank_col = 'bank_name'
    lender_rm_col = 'lender_rm_name'
    stage_col = 'lender_stage'
    last_action_col = 'last_action_day'

    funnel_date_cols = {
        'Shared / Bank Prospect': q_col,
        'Login': l_col,
        'Sanction': s_col,
        'PF Paid': p_col
    }
    
    # Convert dates safely
    for c in [q_col, l_col, s_col, p_col, last_action_col]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors='coerce')

    # Status Flags
    df['has_login'] = df[l_col].notna() if l_col in df.columns else False
    df['has_sanction'] = df[s_col].notna() if s_col in df.columns else False
    df['has_pf'] = df[p_col].notna() if p_col in df.columns else False

    # Dynamic Aging Calculation (Because we don't have LTB/LCB text buckets anymore)
    if last_action_col in df.columns:
        # We calculate "Days Idle" against the most recent date in the dataset (or today)
        current_date = df[last_action_col].max() if pd.notna(df[last_action_col].max()) else pd.to_datetime('today')
        df['Days_Since_Action'] = (current_date - df[last_action_col]).dt.days
        
        # Build the Buckets matching your screenshots
        def bucket_aging(days):
            if pd.isna(days): return 'Not Acted'
            if days <= 3: return 'A 0-3 Days'
            if days <= 7: return 'B 4-7 Days'
            if days <= 11: return 'C 8-11 Days'
            if days <= 15: return 'D 12-15 Days'
            return 'E More than 15 Days'
        
        df['Action_Bucket'] = df['Days_Since_Action'].apply(bucket_aging)

    # --- SIDEBAR FILTER LOGIC ---
    with st.sidebar:
        # Bank Filter
        all_banks = sorted(df[bank_col].dropna().unique()) if bank_col in df.columns else []
        selected_banks = st.multiselect("Select Banks", all_banks, default=all_banks)

        # Internal RM Filter
        all_rms = sorted(df[rm_col].dropna().unique()) if rm_col in df.columns else []
        selected_rms = st.multiselect("Select Internal RMs", all_rms, default=all_rms)
        
        if q_col in df.columns:
            min_date = df[q_col].min().to_pydatetime() if pd.notna(df[q_col].min()) else datetime(2024, 1, 1)
            max_date = df[q_col].max().to_pydatetime() if pd.notna(df[q_col].max()) else datetime.now()
        else:
            min_date, max_date = datetime(2024, 1, 1), datetime.now()
            
        date_range = st.date_input("Date Shared Range", [min_date, max_date])

    # Apply Filters to create our working DataFrame
    mask = pd.Series(True, index=df.index)
    if bank_col in df.columns:
        mask = mask & df[bank_col].isin(selected_banks)
    if rm_col in df.columns:
        mask = mask & df[rm_col].isin(selected_rms)
    if len(date_range) == 2 and q_col in df.columns:
        mask = mask & (df[q_col].dt.date >= date_range[0]) & (df[q_col].dt.date <= date_range[1])
    
    f_df = df[mask].copy()

    # --- TOP LEVEL METRICS ---
    t_shared = len(f_df)
    t_login = int(f_df['has_login'].sum())
    t_sanction = int(f_df['has_sanction'].sum())
    t_pf = int(f_df['has_pf'].sum())
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current PFs", t_pf, delta=f"{t_pf - pf_target}")
    m2.metric("Logins", t_login)
    m3.metric("Sanctions", t_sanction)
    m4.metric("Login to PF Conv. %", f"{(t_pf/t_login*100):.1f}%" if t_login > 0 else "0%")

    # --- TABS ---
    tab_funnel, tab_aging, tab_bank_perf, tab_ai, tab_priority = st.tabs([
        "📊 Pipeline Funnel", "⏱️ Action Aging Matrix", "🏦 Bank & RM Perf", "✨ AI Audit", "🔥 Hit-List"
    ])

    # ==========================================
    # TAB 1: OVERALL FUNNEL
    # ==========================================
    with tab_funnel:
        st.subheader("Lead Progression Funnel")
        funnel_data = []
        for stage_name, date_c in funnel_date_cols.items():
            if date_c in f_df.columns:
                count = f_df[date_c].notna().sum()
                funnel_data.append({'Stage': stage_name, 'Total Reached': count})
        
        if funnel_data:
            funnel_df = pd.DataFrame(funnel_data)
            fig_funnel = px.funnel(funnel_df, x='Total Reached', y='Stage', 
                                   title="Overall Pipeline Funnel",
                                   color_discrete_sequence=['#4f46e5'])
            st.plotly_chart(fig_funnel, use_container_width=True)
            st.dataframe(funnel_df, use_container_width=True, hide_index=True)

    # ==========================================
    # TAB 2: ACTION AGING MATRIX
    # ==========================================
    with tab_aging:
        st.subheader("⏱️ Days Since Last Action Matrix")
        st.write("Tracks how long leads have been sitting without an update (based on `last_action_day`).")
        
        if 'Action_Bucket' in f_df.columns and rm_col in f_df.columns:
            # Pivot by Internal RM
            pivot_rm = pd.crosstab(f_df[rm_col], f_df['Action_Bucket'], margins=True, margins_name='OVERALL')
            
            bucket_order = ['A 0-3 Days', 'B 4-7 Days', 'C 8-11 Days', 'D 12-15 Days', 'E More than 15 Days', 'Not Acted']
            cols = [c for c in bucket_order if c in pivot_rm.columns] + \
                   [c for c in pivot_rm.columns if c not in bucket_order and c != 'OVERALL'] + \
                   (['OVERALL'] if 'OVERALL' in pivot_rm.columns else [])
            
            pivot_rm = pivot_rm.reindex(columns=list(dict.fromkeys(cols)))
            if 'OVERALL' in pivot_rm.columns:
                pivot_rm = pivot_rm.sort_values(by='OVERALL', ascending=False)
                
            st.markdown("#### Internal Advisor Action Aging")
            st.dataframe(pivot_rm.style.background_gradient(cmap='Purples', axis=None), use_container_width=True)
            
            st.divider()

            # Pivot by Bank RM
            if lender_rm_col in f_df.columns:
                pivot_bank_rm = pd.crosstab(f_df[lender_rm_col], f_df['Action_Bucket'], margins=True, margins_name='OVERALL')
                pivot_bank_rm = pivot_bank_rm.reindex(columns=list(dict.fromkeys(cols)))
                if 'OVERALL' in pivot_bank_rm.columns:
                    pivot_bank_rm = pivot_bank_rm.sort_values(by='OVERALL', ascending=False)
                
                st.markdown("#### Bank RM Action Aging (Who is stalling?)")
                st.dataframe(pivot_bank_rm.style.background_gradient(cmap='Blues', axis=None), use_container_width=True)

    # ==========================================
    # TAB 3: BANK & RM RANKINGS
    # ==========================================
    with tab_bank_perf:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Internal RM Leaderboard")
            lb_rm = f_df.groupby(rm_col).agg(
                Logins=('has_login', 'sum'),
                Sanctions=('has_sanction', 'sum'),
                PFs=('has_pf', 'sum')
            ).sort_values('PFs', ascending=False)
            st.dataframe(lb_rm.style.background_gradient(cmap='Greens', subset=['PFs', 'Sanctions']), use_container_width=True)
            
        with col2:
            st.subheader("Bank Performance")
            lb_bank = f_df.groupby(bank_col).agg(
                Logins=('has_login', 'sum'),
                Sanctions=('has_sanction', 'sum'),
                PFs=('has_pf', 'sum')
            ).sort_values('PFs', ascending=False)
            st.dataframe(lb_bank.style.background_gradient(cmap='Greens', subset=['PFs', 'Sanctions']), use_container_width=True)

    # ==========================================
    # TAB 4: TARGETED BANK MEETING AUDIT
    # ==========================================
    with tab_ai:
        st.subheader("🕵️ Bank Meeting Prep: Objective Auditor")
        st.write("Generates a ruthless performance breakdown based on current filters. Highlights Lender RM and Location bottlenecks.")
        
        if st.button("🚀 Generate Meeting Agenda"):
            if not API_KEY:
                st.error("Please add GEMINI_API_KEY to Streamlit Secrets.")
            else:
                with st.spinner("Compiling cross-examination data..."):
                    try:
                        # Find the best model
                        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        best_model = next((m for m in available if '3.1-flash' in m), 
                                     next((m for m in available if '3-flash' in m), 
                                     next((m for m in available if '1.5-flash' in m), 
                                     available[0] if available else None)))

                        if best_model:
                            model = genai.GenerativeModel(best_model)
                            
                            # --- 1. PREPARE SURGICAL DATA FOR AI ---
                            # Filter out 'Lost' leads for accurate Aging (we don't care how long a lost lead has been dead)
                            active_mask = ~f_df[stage_col].astype(str).str.contains('Lost', case=False, na=False)
                            active_df = f_df[active_mask]
                            
                            # Bank/Filter Level Averages
                            overall_idle = active_df['Days_Since_Action'].mean() if 'Days_Since_Action' in active_df.columns else 0
                            
                            # Lender RM Stats
                            if lender_rm_col in f_df.columns:
                                rm_stats = f_df.groupby(lender_rm_col).agg(
                                    Shared=('has_login', 'count'), # Total leads assigned
                                    Logins=('has_login', 'sum'),
                                    Sanctions=('has_sanction', 'sum'),
                                    PFs=('has_pf', 'sum')
                                )
                                # Add Active Idle Days
                                if 'Days_Since_Action' in active_df.columns:
                                    rm_stats['Active_Avg_Idle'] = active_df.groupby(lender_rm_col)['Days_Since_Action'].mean()
                                
                                rm_stats_str = rm_stats.fillna(0).round(1).reset_index().to_string(index=False)
                            else:
                                rm_stats_str = "Lender RM data not available."

                            # Location Stats
                            loc_col = 'location' # Matching your CSV header
                            if loc_col in f_df.columns:
                                loc_stats = f_df.groupby(loc_col).agg(
                                    Shared=('has_login', 'count'),
                                    Logins=('has_login', 'sum'),
                                    Sanctions=('has_sanction', 'sum')
                                )
                                if 'Days_Since_Action' in active_df.columns:
                                    loc_stats['Active_Avg_Idle'] = active_df.groupby(loc_col)['Days_Since_Action'].mean()
                                    
                                loc_stats_str = loc_stats.fillna(0).round(1).reset_index().to_string(index=False)
                            else:
                                loc_stats_str = "Location data not available."

                            # --- 2. THE RUTHLESS PROMPT ---
                            prompt = f"""
                            You are an elite Data Analyst preparing your Director for a B2B performance review meeting with the currently filtered Bank partner.
                            
                            Here is the Bank's Overall Active Idle Average: {overall_idle:.1f} days.
                            
                            YOUR BENCHMARKS (Do not compromise on these):
                            1. Shared to Login Conversion MUST be 90% or higher.
                            2. Login to Sanction Conversion MUST be 85% or higher.
                            
                            Analyze the data below and output a strict, bulleted meeting agenda. Use these exact headings:

                            ### 1. ⏱️ Aging Outliers (Lender RMs)
                            Identify specific Lender RMs whose 'Active_Avg_Idle' is significantly higher than the overall average of {overall_idle:.1f} days. Name them and state their idle time.

                            ### 2. 📉 Conversion Failures (Lender RMs)
                            Calculate the 'Shared to Login' and 'Login to Sanction' percentages for the Lender RMs. Explicitly name the RMs who are failing to hit the 90% Login and 85% Sanction benchmarks. 

                            ### 3. 📍 Location Bottlenecks
                            Analyze the Location data. Identify which specific cities are dragging down the average through either high idle times or terrible conversion rates against our benchmarks.

                            ### 4. 🎯 The "Hard Ask"
                            Give me one aggressive but professional question to ask the Bank's leadership in this meeting to force them to fix the worst bottleneck identified above.

                            --- DATA ---
                            LENDER RM PERFORMANCE:
                            {rm_stats_str}
                            
                            LOCATION PERFORMANCE:
                            {loc_stats_str}
                            """
                            
                            response = model.generate_content(prompt)
                            st.success("✅ Meeting Prep Generated")
                            st.markdown("---")
                            st.markdown(response.text)
                        else:
                            st.error("No compatible models found.")
                    except Exception as e:
                        st.error(f"🤖 AI Error: {e}")
    # ==========================================
    # TAB 5: HIT-LIST
    # ==========================================
    with tab_priority:
        st.subheader("🔥 High-Probability Leads (Active Pipeline)")
        
        # Only include active leads (Not Lost, Not PF Paid)
        active = f_df[~f_df['has_pf'] & (f_df[stage_col].str.lower() != 'lost')].copy()
        
        active['Score'] = 0
        if stage_col in active.columns:
            active.loc[active[stage_col].str.contains('Sanction', case=False, na=False), 'Score'] += 50
            active.loc[active[stage_col].str.contains('Login', case=False, na=False), 'Score'] += 30
            active.loc[active[stage_col].str.contains('Bank Prospect', case=False, na=False), 'Score'] += 10
            
        # Penalize leads that haven't been acted on in a long time (Over 10 Days idle)
        if 'Days_Since_Action' in active.columns:
            active.loc[active['Days_Since_Action'] > 10, 'Score'] -= 15
            
        hit_list = active.sort_values('Score', ascending=False).head(25)
        
        # Display the Hit List including the Lender RM so your team knows who to call!
        display_cols = ['Score', rm_col, bank_col, lender_rm_col, stage_col, last_action_col]
        display_cols = [c for c in display_cols if c in hit_list.columns]
        
        st.dataframe(hit_list[display_cols].style.background_gradient(cmap='Oranges', subset=['Score']), use_container_width=True, hide_index=True)

else:
    st.info("👋 Welcome! Please upload your 'Bank Meetings' CSV in the sidebar to begin.")
