# p.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import time
from config import *
from utils import *
from datetime import datetime, timedelta

st.set_page_config(
    page_title=PAGE_TITLE,
    layout="wide",
    page_icon=PAGE_ICON,
    initial_sidebar_state="expanded"
)

# Logo + Title
col_logo, col_title = st.columns([1, 5])
with col_logo:
    try:
        st.image(LOGO_PATH, width=100)
    except:
        st.write(PAGE_ICON)
with col_title:
    st.title(f"{PAGE_TITLE}")
    st.caption(f"by {AUTHOR}")

@st.cache_data
def load_data():
    start = time.time()
    df = pd.read_parquet(DATA_PATH, engine='pyarrow')

    # Parse date column - safe check
    if DATE_COLUMN and DATE_COLUMN in df.columns:
        df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], errors='coerce')

    df['bill_amount'] = df['bill_amount'].replace(0, np.nan)
    df['payment_percent'] = (df['previous_payments'] / df['bill_amount'] * 100).fillna(0)

    conditions = [
        (df['payment_percent'] < RISK_THRESHOLDS['high_risk_payment_pct']) &
        (df['closing_balance'] > RISK_THRESHOLDS['high_risk_balance']),
        (df['payment_percent'] < RISK_THRESHOLDS['medium_risk_payment_pct'])
    ]
    choices = ['High Risk', 'Medium Risk']
    df['risk'] = np.select(conditions, choices, default='Low Risk')

    df['z_score'] = (df['bill_amount'] - df['bill_amount'].mean()) / df['bill_amount'].std()

    load_time = time.time() - start
    return df, load_time

df, load_time = load_data()
st.sidebar.caption(f"⚡ Loaded {len(df):,} rows in {load_time:.2f}s")

# -------------------------------
# KPI Metrics
# -------------------------------
total_billed = df['bill_amount'].sum()
total_payments = df['previous_payments'].sum()
total_debt = df['closing_balance'].sum()
total_energy = df['consumption'].sum() if 'consumption' in df.columns else 0
payment_rate = (total_payments / total_billed * 100) if total_billed > 0 else 0

st.subheader("📊 Key Metrics")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Energy Billed", KWH_FORMAT.format(total_energy))
col2.metric("Total Amount Billed", NAIRA_FORMAT.format(total_billed))
col3.metric("Total Payments", NAIRA_FORMAT.format(total_payments))
col4.metric("Outstanding Balance", NAIRA_FORMAT.format(total_debt),
            delta=PERCENT_FORMAT.format(payment_rate - COLLECTION_TARGET) + " vs target")

outliers = df[np.abs(df['z_score']) > OUTLIER_Z_THRESHOLD]

# -------------------------------
# ZIMICO Band Performance
# -------------------------------
st.subheader("⚡ TARIFF, FEEDER, CUSTOMER TYPE AND BILLING STYLE PERFORMANCE" , text_alignment="center")
band_col1, band_col2, band_col3 = st.columns([2,2,2])
with band_col1:
    if 'tariff' in df.columns:
        band_summary = df.groupby('tariff').agg({
            'account_number': 'count',
            "consumption": 'sum',
            'bill_amount': 'sum',
        }).reset_index()
        
        st.dataframe(
            band_summary,
            use_container_width=True,
            column_config={
                "account_number": st.column_config.NumberColumn("Population"),
                "consumption": st.column_config.NumberColumn("Energy Billed (kWh)", format="%.0f"),
                "bill_amount": st.column_config.NumberColumn("Amount Billed (₦)", format="%.0f"),
                
            }
        )

with band_col2:
    if 'feeder' in df.columns:
        feeder_summary = df.groupby('feeder').agg({
            'account_number': 'count',
            "consumption": 'sum',
            'bill_amount': 'sum',
        }).reset_index()
         
        st.dataframe(
            feeder_summary,
            use_container_width=True,
            column_config={
                "account_number": st.column_config.NumberColumn("Population"),
                "consumption": st.column_config.NumberColumn("Energy Billed (kWh)", format="%.0f"),
                "bill_amount": st.column_config.NumberColumn("Amount Billed (₦)", format="%.0f"),
                 }
            )

with band_col3:
    if 'type' in df.columns:
        summary_by_type  = df.groupby('type').agg({
            'account_number': 'count',
            "consumption": 'sum',
            'bill_amount': 'sum',
       
        }).reset_index()
        st.dataframe(
             summary_by_type,
            use_container_width=True,
            column_config={
               "account_number": st.column_config.NumberColumn("Population"),
               "consumption": st.column_config.NumberColumn("Energy Billed (kWh)", format="%.0f"),
               "bill_amount": st.column_config.NumberColumn("Amount Billed (₦)", format="%.0f"),
             
                 
            }
        )

    if 'bill_style' in df.columns:
        summary_by_bill_style  = df.groupby('bill_style').agg({
            'account_number': 'count',
            "consumption": 'sum',
            'bill_amount': 'sum',
       
        }).reset_index()
        st.dataframe(
             summary_by_bill_style,
            use_container_width=True,
            column_config={
               "account_number": st.column_config.NumberColumn("Population"),
               "consumption": st.column_config.NumberColumn("Energy Billed (kWh)", format="%.0f"),
               "bill_amount": st.column_config.NumberColumn("Amount Billed (₦)", format="%.0f"),
             
                 
            }
        )
# -------------------------------
# Sidebar filters
# -------------------------------
st.sidebar.header("Filters")

# Date filter - uses 'period' column
start_date = end_date = None
if DATE_COLUMN and DATE_COLUMN in df.columns and df[DATE_COLUMN].notna().any():
    min_date = df[DATE_COLUMN].min().date()
    max_date = df[DATE_COLUMN].max().date()
    date_range = st.sidebar.date_input(
        "Billing Period",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range[0]
else:
    st.sidebar.info("Date filtering disabled - check 'period' column")

status_option = st.sidebar.selectbox(
    "Payment Status",
    ["All", "Low (<20%)", "Medium (20-50%)", "High (>50%)"]
)

risk_filter = st.sidebar.multiselect("Risk Level", ['Low Risk', 'Medium Risk', 'High Risk'],
                                     default=['Low Risk', 'Medium Risk', 'High Risk'])

# Apply filters
filtered = df.copy()

if start_date and end_date and DATE_COLUMN and DATE_COLUMN in filtered.columns:
    filtered = filtered[
        (filtered[DATE_COLUMN].dt.date >= start_date) &
        (filtered[DATE_COLUMN].dt.date <= end_date)
    ]

if status_option == "Low (<20%)":
    filtered = filtered[filtered['payment_percent'] < RISK_THRESHOLDS['high_risk_payment_pct']]
elif status_option == "Medium (20-50%)":
    filtered = filtered[(filtered['payment_percent'] >= RISK_THRESHOLDS['high_risk_payment_pct']) &
                  (filtered['payment_percent'] <= RISK_THRESHOLDS['medium_risk_payment_pct'])]
elif status_option == "High (>50%)":
    filtered = filtered[filtered['payment_percent'] > RISK_THRESHOLDS['medium_risk_payment_pct']]

filtered = filtered[filtered['risk'].isin(risk_filter)]

# -------------------------------
# Cached Aggregations
# -------------------------------
@st.cache_data
def get_summaries(_df):
    summary_by_feeder = (
        _df.groupby('feeder', as_index=False)
      .agg(
            Population=('account_number', 'count'),
            Energy_Billed=('consumption', 'sum'),
            Amount_Billed=('bill_amount', 'sum'),
            Payments=('previous_payments', 'sum'),
            Outstanding=('closing_balance', 'sum')
        )
      .sort_values('Amount_Billed', ascending=False)
    )
    summary_by_feeder['Collection %'] = (summary_by_feeder['Payments'] / summary_by_feeder['Amount_Billed'] * 100).fillna(0)

    summary_by_tariff = (
        _df.groupby('tariff', as_index=False)
      .agg(
            Population=('account_number', 'count'),
            Energy_Billed=('consumption', 'sum'),
            Amount_Billed=('bill_amount', 'sum'),
            Payments=('previous_payments', 'sum')
        )
      .sort_values('Amount_Billed', ascending=False)
    )
    summary_by_tariff['Collection %'] = (summary_by_tariff['Payments'] / summary_by_tariff['Amount_Billed'] * 100).fillna(0)

    summary_by_bill_style = (
        _df.groupby('bill_style', as_index=False)
      .agg(
            Population=('account_number', 'count'),
            Energy_Billed=('consumption', 'sum'),
            Amount_Billed=('bill_amount', 'sum'),
            Payments=('previous_payments', 'sum')
        )
      .sort_values('Amount_Billed', ascending=False)
    )

    summary_by_type = (
        _df.groupby('type', as_index=False)
      .agg(
            Population=('account_number', 'count'),
            Energy_Billed=('consumption', 'sum'),
            Amount_Billed=('bill_amount', 'sum'),
            Payments=('previous_payments', 'sum'),
            Outstanding=('closing_balance', 'sum')
        )
      .sort_values('Amount_Billed', ascending=False)
    )

    top_customers = _df.nlargest(TOP_N_DEBTORS, 'closing_balance')[
        ['account_number','feeder', 'tariff', 'consumption','bill_amount', 'previous_payments', 'closing_balance', 'risk']
    ]

    return summary_by_feeder, summary_by_tariff, summary_by_bill_style, summary_by_type, top_customers

feeder_sum, tariff_sum, billstyle_sum, type_sum, top_customers = get_summaries(filtered)

# -------------------------------
# Aggregated Views
# -------------------------------
st.subheader("📈 Aggregated Performance")
# Tabs
agg_tab1, agg_tab2, agg_tab3, agg_tab4, agg_tab5, agg_tab6, agg_tab7, agg_tab8, agg_tab9 = st.tabs([
    "By Feeder", "By Tariff", "By Bill Style", "By Customer Type", "Top 50 Debtors", 
    "NERC Compliance", "Feeder Scorecards", "Customer Lookup", "Revenue Alerts"
])

with agg_tab9:
    st.markdown(f"### 🚨 {COMPANY_NAME} - Revenue Protection Alerts")
    st.caption("Automated detection of revenue leakage and fraud patterns")

    if st.button("🔍 Run Revenue Protection Scan", key="rp_scan_btn", type="primary", use_container_width=True):
        with st.spinner("Scanning for revenue risks..."):
            alerts = generate_revenue_alerts(filtered, {
                'MAJOR_FEEDERS': MAJOR_FEEDERS
            })

        if not alerts:
            st.success("✅ No revenue alerts detected. All accounts within normal parameters.")
        else:
            st.error(f"⚠️ {len(alerts)} Alert Types Detected")

            total_risk = sum(a['total_at_risk'] for a in alerts)
            col_a1, col_a2, col_a3 = st.columns(3)
            col_a1.metric("Alert Types", len(alerts))
            col_a2.metric("Accounts Flagged", sum(a['count'] for a in alerts))
            col_a3.metric("Total at Risk", NAIRA_FORMAT.format(total_risk))

            for alert in alerts:
                with st.expander(f"{alert['severity']}: {alert['type']} - {alert['count']} accounts", expanded=alert['severity']=='CRITICAL'):
                    st.write(f"**Amount at Risk:** {NAIRA_FORMAT.format(alert['total_at_risk'])}")
                    st.dataframe(pd.DataFrame(alert['accounts']), use_container_width=True)

            # Export alert report
            email_text = format_alert_email(alerts, COMPANY_NAME)
            st.download_button(
                "📥 Download Alert Report",
                email_text,
                f"ZIMICO_Revenue_Alerts_{datetime.now().strftime('%Y%m%d')}.txt",
                "text/plain",
                use_container_width=True
            )

with agg_tab1:
    st.dataframe(feeder_sum, use_container_width=True, height=400,
        column_config={
            "Energy_Billed": st.column_config.NumberColumn("Energy Billed(kWh)", format="%.0f"),
            "Amount_Billed": st.column_config.NumberColumn("Amount Billed (₦)", format="%.0f"),
            "Payments": st.column_config.NumberColumn("Payments (₦)", format="%.0f"),
            "Outstanding": st.column_config.NumberColumn("Outstanding (₦)", format="%.0f"),
            "Collection %": st.column_config.ProgressColumn("Collection %", format="%.1f%%", min_value=0, max_value=100),
        }
    )
    st.bar_chart(feeder_sum.set_index('feeder')['Amount_Billed'].head(TOP_N_FEEDERS))

with agg_tab2:
     st.dataframe(tariff_sum, use_container_width=True, height=400,
        column_config={
            "Energy_Billed": st.column_config.NumberColumn("Energy Billed(kWh)", format="%.0f"),
            "Amount_Billed": st.column_config.NumberColumn("Amount Billed (₦)", format="%.0f"),
            "Payments": st.column_config.NumberColumn("Payments (₦)", format="%.0f"),
            "Outstanding": st.column_config.NumberColumn("Outstanding (₦)", format="%.0f"),
            "Collection %": st.column_config.ProgressColumn("Collection %", format="%.1f%%", min_value=0, max_value=100),
        }
     )
     st.bar_chart(tariff_sum.set_index('tariff')['Amount_Billed'].head(TOP_N_FEEDERS))
with agg_tab3:
    st.dataframe(billstyle_sum, use_container_width=True)
with agg_tab4:
    st.dataframe(type_sum, use_container_width=True)
with agg_tab5:
    st.dataframe(top_customers, use_container_width=True)

with agg_tab6:
    st.markdown(f"### {COMPANY_NAME} - NERC Compliance Report")

    # Check if date column exists for comparison
    if DATE_COLUMN and DATE_COLUMN in df.columns and df[DATE_COLUMN].notna().any():
        # Create month selector
        df['month_year'] = df[DATE_COLUMN].dt.to_period('M')
        available_months = sorted(df['month_year'].unique(), reverse=True)
        month_options = [str(m) for m in available_months]

        st.markdown("#### Select Periods to Compare")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            month1 = st.selectbox("Current Period", month_options, index=0, key="m1")
        with col_m2:
            month2 = st.selectbox("Compare With", month_options, index=1 if len(month_options) > 1 else 0, key="m2")

        # Filter data for both months
        df_m1 = df[df['month_year'] == pd.Period(month1)]
        df_m2 = df[df['month_year'] == pd.Period(month2)]

        nerc_m1 = calculate_nerc_metrics(df_m1)
        nerc_m2 = calculate_nerc_metrics(df_m2)

        st.divider()
        
        # Compliance status for both periods
        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            if nerc_m1['overall_compliant']:
                st.success(f"✅ {month1}: COMPLIANT")
            else:
                st.error(f"⚠️ {month1}: NON-COMPLIANT")
        with col_stat2:
            if nerc_m2['overall_compliant']:
                st.success(f"✅ {month2}: COMPLIANT")
            else:
                st.error(f"⚠️ {month2}: NON-COMPLIANT")

        # MoM Comparison Table
        st.subheader("📊 Month-on-Month Performance")
        
        comp_data = {
            'NERC KPI': ['Billing Efficiency', 'Collection Efficiency', 'ATC&C Losses', 'Energy Billed (kWh)', 'Revenue Collected (₦)', 'Accounts'],
            month1: [
                PERCENT_FORMAT.format(nerc_m1['billing_efficiency']),
                PERCENT_FORMAT.format(nerc_m1['collection_efficiency']),
                PERCENT_FORMAT.format(nerc_m1['atcc_losses']),
                KWH_FORMAT.format(nerc_m1['energy_billed']),
                NAIRA_FORMAT.format(nerc_m1['revenue_collected']),
                f"{len(df_m1):,}"
            ],
            month2: [
                PERCENT_FORMAT.format(nerc_m2['billing_efficiency']),
                PERCENT_FORMAT.format(nerc_m2['collection_efficiency']),
                PERCENT_FORMAT.format(nerc_m2['atcc_losses']),
                KWH_FORMAT.format(nerc_m2['energy_billed']),
                NAIRA_FORMAT.format(nerc_m2['revenue_collected']),
                f"{len(df_m2):,}"
            ],
            'Change': [
                PERCENT_FORMAT.format(nerc_m1['billing_efficiency'] - nerc_m2['billing_efficiency']),
                PERCENT_FORMAT.format(nerc_m1['collection_efficiency'] - nerc_m2['collection_efficiency']),
                PERCENT_FORMAT.format(nerc_m1['atcc_losses'] - nerc_m2['atcc_losses']),
                KWH_FORMAT.format(nerc_m1['energy_billed'] - nerc_m2['energy_billed']),
                NAIRA_FORMAT.format(nerc_m1['revenue_collected'] - nerc_m2['revenue_collected']),
                f"{len(df_m1) - len(df_m2):,}"
            ],
            'Trend': [
                '🟢 Improved' if nerc_m1['billing_efficiency'] >= nerc_m2['billing_efficiency'] else '🔴 Declined',
                '🟢 Improved' if nerc_m1['collection_efficiency'] >= nerc_m2['collection_efficiency'] else '🔴 Declined',
                '🟢 Improved' if nerc_m1['atcc_losses'] <= nerc_m2['atcc_losses'] else '🔴 Declined',
                '🟢' if nerc_m1['energy_billed'] >= nerc_m2['energy_billed'] else '🔴',
                '🟢' if nerc_m1['revenue_collected'] >= nerc_m2['revenue_collected'] else '🔴',
                '🟢' if len(df_m1) >= len(df_m2) else '🔴'
            ]
        }
        
        st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)
        
        # Detailed KPI cards for current month
        st.subheader(f"🎯 NERC Targets - {month1}")
        target_col1, target_col2, target_col3 = st.columns(3)
        
        with target_col1:
            delta_be = nerc_m1['billing_efficiency'] - NERC_TARGETS['billing_efficiency']
            st.metric(
                "Billing Efficiency",
                PERCENT_FORMAT.format(nerc_m1['billing_efficiency']),
                delta=PERCENT_FORMAT.format(delta_be),
                delta_color="normal" if nerc_m1['billing_ok'] else "inverse"
            )
            st.progress(min(nerc_m1['billing_efficiency'] / 100, 1.0))
            st.caption(f"Target: ≥{NERC_TARGETS['billing_efficiency']}% | Prev: {PERCENT_FORMAT.format(nerc_m2['billing_efficiency'])}")
            
        with target_col2:
            delta_ce = nerc_m1['collection_efficiency'] - NERC_TARGETS['collection_efficiency']
            st.metric(
                "Collection Efficiency",
                PERCENT_FORMAT.format(nerc_m1['collection_efficiency']),
                delta=PERCENT_FORMAT.format(delta_ce),
                delta_color="normal" if nerc_m1['collection_ok'] else "inverse"
            )
            st.progress(min(nerc_m1['collection_efficiency'] / 100, 1.0))
            st.caption(f"Target: ≥{NERC_TARGETS['collection_efficiency']}% | Prev: {PERCENT_FORMAT.format(nerc_m2['collection_efficiency'])}")
            
        with target_col3:
            delta_atcc = NERC_TARGETS['atcc_target'] - nerc_m1['atcc_losses']
            st.metric(
                "ATC&C Losses",
                PERCENT_FORMAT.format(nerc_m1['atcc_losses']),
                delta=PERCENT_FORMAT.format(delta_atcc),
                delta_color="normal" if nerc_m1['atcc_ok'] else "inverse"
            )
            atcc_progress = max(0, 1 - (nerc_m1['atcc_losses'] / 100))
            st.progress(atcc_progress)
            st.caption(f"Target: ≤{NERC_TARGETS['atcc_target']}% | Prev: {PERCENT_FORMAT.format(nerc_m2['atcc_losses'])}")

        # Export
        comp_df = pd.DataFrame(comp_data)
        st.download_button(
            "📥 Export MoM Comparison",
            comp_df.to_csv(index=False).encode('utf-8'),
            f"ZIMICO_NERC_MoM_{month1}_vs_{month2}.csv",
            "text/csv",
            use_container_width=True
        )

        st.divider()
        st.markdown("**PDF Report for NERC Submission**")
        if st.button("📄 Generate PDF Report", key="nerc_pdf_btn", use_container_width=True, type="primary"):
            pdf_buffer = generate_nerc_pdf_report(df_m1, nerc_m1, month1, LOGO_PATH)
            st.download_button(
                "⬇️ Download ZIMICO NERC Report",
                pdf_buffer,
                f"ZIMICO_NERC_Report_{month1}.pdf",
                "application/pdf",
                use_container_width=True
            )
    else:
        st.warning("Configure DATE_COLUMN in config.py to enable month-on-month comparison.")

with agg_tab7:
    st.markdown(f"### {COMPANY_NAME} - Feeder Revenue Protection Scorecard")
    st.caption("Ranked by risk score. Higher score means worse collection performance.")

    # Calculate feeder-level metrics
    feeder_nerc = filtered.groupby('feeder').agg({
        'consumption': 'sum',
        'bill_amount': 'sum',
        'previous_payments': 'sum',
        'closing_balance': 'sum',
        'account_number': 'count'
    }).reset_index()
    
    feeder_nerc['Collection_Eff'] = (feeder_nerc['previous_payments'] / feeder_nerc['bill_amount'] * 100).fillna(0)
    feeder_nerc['Outstanding_%'] = (feeder_nerc['closing_balance'] / feeder_nerc['bill_amount'] * 100).fillna(0)
    feeder_nerc['Revenue_per_Customer'] = feeder_nerc['bill_amount'] / feeder_nerc['account_number']
    feeder_nerc['Risk_Score'] = 100 - feeder_nerc['Collection_Eff']
    
    # Flag major feeders
    feeder_nerc['Priority'] = feeder_nerc['feeder'].apply(lambda x: '⭐ Major' if x in MAJOR_FEEDERS else 'Standard')
    
    # Rank worst 10
    worst_feeders = feeder_nerc.nlargest(10, 'Risk_Score')
    best_feeders = feeder_nerc.nsmallest(5, 'Risk_Score')
    
    col_worst, col_best = st.columns(2)
    
    with col_worst:
        st.error(f"🚨 **Worst 10 Feeders - Immediate Action Required**")
        st.dataframe(
            worst_feeders[['feeder', 'account_number', 'bill_amount', 'previous_payments', 'Collection_Eff', 'Outstanding_%', 'Risk_Score', 'Priority']],
            use_container_width=True,
            column_config={
                "account_number": st.column_config.NumberColumn("Customers", format="%d"),
                "bill_amount": st.column_config.NumberColumn("Billed (₦)", format="%.0f"),
                "previous_payments": st.column_config.NumberColumn("Collected (₦)", format="%.0f"),
                "Collection_Eff": st.column_config.ProgressColumn("Collection %", format="%.1f%%", min_value=0, max_value=100),
                "Outstanding_%": st.column_config.NumberColumn("Outstanding %", format="%.1f%%"),
                "Risk_Score": st.column_config.ProgressColumn("Risk", format="%.0f", min_value=0, max_value=100),
            },
            hide_index=True
        )
    
    with col_best:
        st.success(f"✅ **Top 5 Performing Feeders**")
        st.dataframe(
            best_feeders[['feeder', 'account_number', 'Collection_Eff', 'Revenue_per_Customer']],
            use_container_width=True,
            column_config={
                "account_number": st.column_config.NumberColumn("Customers", format="%d"),
                "Collection_Eff": st.column_config.ProgressColumn("Collection %", format="%.1f%%", min_value=0, max_value=100),
                "Revenue_per_Customer": st.column_config.NumberColumn("Rev/Customer (₦)", format="%.0f"),
            },
            hide_index=True
        )
    
    st.divider()
    
    # Full feeder list
    st.markdown("**All Feeders - Sorted by Risk**")
    st.dataframe(
        feeder_nerc.sort_values('Risk_Score', ascending=False),
        use_container_width=True,
        height=400,
        column_config={
            "account_number": st.column_config.NumberColumn("Customers", format="%d"),
            "consumption": st.column_config.NumberColumn("Energy (kWh)", format="%.0f"),
            "bill_amount": st.column_config.NumberColumn("Billed (₦)", format="%.0f"),
            "previous_payments": st.column_config.NumberColumn("Collected (₦)", format="%.0f"),
            "closing_balance": st.column_config.NumberColumn("Outstanding (₦)", format="%.0f"),
            "Collection_Eff": st.column_config.ProgressColumn("Collection %", format="%.1f%%", min_value=0, max_value=100),
            "Risk_Score": st.column_config.ProgressColumn("Risk", format="%.0f", min_value=0, max_value=100),
        }
    )
    
    st.download_button(
        "📥 Export Feeder Scorecard",
        feeder_nerc.to_csv(index=False).encode('utf-8'),
        f"ZIMICO_Feeder_Scorecard_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv"
    )

with agg_tab8:
    st.markdown(f"### {COMPANY_NAME} - Customer Account Lookup")
    st.caption("Search account, view payment history, generate demand notices")

    # Search form - only runs when button clicked
    with st.form(key="customer_search_form"):
        col_search1, col_search2 = st.columns([4, 1])
        with col_search1:
            search_account = st.text_input(
                "Enter Account Number",
                placeholder="e.g. 12345678",
                key="account_search_input"
            )
        with col_search2:
            st.write("") # spacing
            st.write("") # spacing
            search_clicked = st.form_submit_button("🔍 Search", use_container_width=True, type="primary")

    # Only run search when button is clicked
    if search_clicked:
        if not search_account:
            st.warning("Please enter an account number to search")
        else:
            customer_data = df[df['account_number'].astype(str) == str(search_account)]

            if len(customer_data) == 0:
                st.error(f"Account {search_account} not found in database")
            else:
                cust = customer_data.iloc[0]

                # Customer summary cards
                st.divider()
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Account", cust['account_number'])
                col2.metric("Feeder", cust['feeder'])
                col3.metric("Tariff Band", cust['tariff'])
                col4.metric("Risk Level", cust['risk'])

                col5, col6, col7, col8 = st.columns(4)
                col5.metric("Total Billed", NAIRA_FORMAT.format(cust['bill_amount']))
                col6.metric("Total Paid", NAIRA_FORMAT.format(cust['previous_payments']))
                col7.metric("Outstanding", NAIRA_FORMAT.format(cust['closing_balance']))
                col8.metric("Payment %", PERCENT_FORMAT.format(cust['payment_percent']))

                # Risk warning
                if cust['risk'] == 'High Risk':
                    st.error(f"⚠️ HIGH RISK: {cust['payment_percent']:.1f}% paid, ₦{cust['closing_balance']:,.0f} outstanding")
                elif cust['risk'] == 'Medium Risk':
                    st.warning(f"Medium Risk: {cust['payment_percent']:.1f}% paid")
                else:
                    st.success(f"Low Risk: {cust['payment_percent']:.1f}% paid")

                st.divider()

                # Payment history chart
                st.subheader("📊 Payment History")

                if DATE_COLUMN and DATE_COLUMN in df.columns:
                    cust_history = df[df['account_number'] == cust['account_number']].sort_values(DATE_COLUMN)

                    if len(cust_history) > 1:
                        fig, ax = plt.subplots(figsize=(10, 4))
                        ax.plot(cust_history[DATE_COLUMN], cust_history['bill_amount'], marker='o', label='Billed', color=COLORS['primary'])
                        ax.plot(cust_history[DATE_COLUMN], cust_history['previous_payments'], marker='s', label='Paid', color=COLORS['success'])
                        ax.fill_between(cust_history[DATE_COLUMN], cust_history['previous_payments'], cust_history['bill_amount'],
                                       alpha=0.3, color=COLORS['danger'], label='Outstanding')
                        ax.set_ylabel("Amount (₦)")
                        ax.set_xlabel("Billing Period")
                        ax.legend()
                        ax.grid(True, alpha=0.3)
                        plt.xticks(rotation=45)
                        st.pyplot(fig)

                        # History table
                        st.dataframe(
                            cust_history[['period', 'bill_amount', 'previous_payments', 'closing_balance', 'payment_percent']],
                            use_container_width=True,
                            column_config={
                                "period": st.column_config.DateColumn("Period", format="DD-MM-YYYY"),
                                "bill_amount": st.column_config.NumberColumn("Billed (₦)", format="%.0f"),
                                "previous_payments": st.column_config.NumberColumn("Paid (₦)", format="%.0f"),
                                "closing_balance": st.column_config.NumberColumn("Balance (₦)", format="%.0f"),
                                "payment_percent": st.column_config.ProgressColumn("Payment %", format="%.1f%%", min_value=0, max_value=100),
                            },
                            hide_index=True
                        )
                    else:
                        st.info("Only 1 billing record found for this account")
                else:
                    st.info("Date column not configured. Showing current snapshot only.")

                st.divider()

                # Demand Notice Generator
                st.subheader("📄 Generate Demand Notice")

                if cust['closing_balance'] > 0:
                    col_dn1, col_dn2 = st.columns([2, 1])

                    with col_dn1:
                        days_overdue = st.number_input("Days Overdue", min_value=1, value=90, step=30, key="days_overdue_input")
                        disconnection_date = st.date_input("Proposed Disconnection Date",
                                                           value=datetime.now().date() + pd.Timedelta(days=14),
                                                           key="disconnection_date_input")

                    with col_dn2:
                        st.write("")
                        generate_dn = st.button("Generate Demand Letter", key="demand_letter_btn", use_container_width=True, type="primary")

                    if generate_dn:
                        demand_letter = f"""
KANO ELECTRICITY DISTRIBUTION COMPANY PLC
{OPERATIONAL_DATA['reporting_month']}

FINAL DEMAND NOTICE

Account Number: {cust['account_number']}
Customer Name: [Customer Name]
Feeder: {cust['feeder']}
Tariff: {cust['tariff']}

Dear Customer,

FINAL DEMAND FOR PAYMENT OF OUTSTANDING ELECTRICITY BILL

Our records show that your account has an outstanding balance of {NAIRA_FORMAT.format(cust['closing_balance'])} which has been overdue for {days_overdue} days.

SUMMARY OF OUTSTANDING:
Total Amount Billed: {NAIRA_FORMAT.format(cust['bill_amount'])}
Total Amount Paid: {NAIRA_FORMAT.format(cust['previous_payments'])}
Outstanding Balance: {NAIRA_FORMAT.format(cust['closing_balance'])}
Payment Performance: {PERCENT_FORMAT.format(cust['payment_percent'])}

In accordance with NERC regulations, you are hereby given 14 days from the date of this notice to settle the outstanding amount.

Failure to pay the full amount by {disconnection_date.strftime('%d-%m-%Y')} will result in disconnection of electricity supply to your premises without further notice.

Payment can be made at any ZIMICO office, authorized payment centers, or via online platforms.

For enquiries, contact: ZIMICO Customer Care

Yours faithfully,
Revenue Protection Department
Kano Electricity Distribution Company Plc

Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}
"""
                        st.text_area("Demand Notice Preview", demand_letter, height=400, key="demand_letter_preview")
                        st.download_button(
                            "⬇️ Download Demand Letter",
                            demand_letter,
                            f"ZIMICO_Demand_Notice_{cust['account_number']}_{datetime.now().strftime('%Y%m%d')}.txt",
                            "text/plain",
                            use_container_width=True,
                            key="demand_letter_download"
                        )
                else:
                    st.success("✅ Account has zero outstanding balance. No demand notice needed.")

                # Full record table
                st.divider()
                st.markdown("**Complete Account Record**")
                st.dataframe(customer_data, use_container_width=True)


# -------------------------------
# Customer List
# -------------------------------
st.subheader(f"📋 Customer List: {len(filtered):,} accounts")
st.dataframe(
    filtered[['account_number','consumption','bill_amount','previous_payments','payment_percent','closing_balance','risk']],
    use_container_width=True, height=600,
    column_config={
        "consumption": st.column_config.NumberColumn("Energy (kWh)", format="%.0f"),
        "bill_amount": st.column_config.NumberColumn("Bill Amount (₦)", format="%.0f"),
        "previous_payments": st.column_config.NumberColumn("Payments (₦)", format="%.0f"),
        "closing_balance": st.column_config.NumberColumn("Outstanding (₦)", format="%.0f"),
        "payment_percent": st.column_config.NumberColumn("Payment %", format="%.1f%%"),
    }
)

# -------------------------------
# Charts
# -------------------------------
st.subheader(f"📊 Top {TOP_N_CUSTOMERS} Outstanding Balances")
top_n = filtered.nlargest(TOP_N_CUSTOMERS, 'closing_balance')
fig, ax = plt.subplots(figsize=(12,5))
colors = [COLORS['danger'] if x == 0 else COLORS['warning'] for x in top_n['payment_percent']]
ax.bar(top_n['account_number'].astype(str), top_n['closing_balance'], color=colors)
plt.xticks(rotation=75)
plt.ylabel("Outstanding (₦)")
ax.set_title("Red = Zero payments", color=COLORS['primary'])
st.pyplot(fig)

tab1, tab2 = st.tabs(["⚠ High-Risk Customers", "💡 Outlier Bills"])
with tab1:
    high_risk = filtered[filtered['risk'] == 'High Risk']
    st.dataframe(high_risk[['account_number','bill_amount','previous_payments','closing_balance','payment_percent']], use_container_width=True)
with tab2:
    st.dataframe(outliers[['account_number','bill_amount','z_score']], use_container_width=True)

st.subheader("🔥 Payment & Balance Heatmap")
heat_data = filtered[['bill_amount','previous_payments','payment_percent','closing_balance']].head(HEATMAP_ROWS)
fig, ax = plt.subplots(figsize=(10,6))
sns.heatmap(heat_data, annot=False, cmap="YlOrRd", ax=ax)
st.pyplot(fig)

st.sidebar.divider()
st.sidebar.download_button(
    "📥 Export Filtered Data",
    filtered.to_csv(index=False).encode('utf-8'),
    f"ZIMICO_AR_{start_date}_{end_date}_{datetime.now().strftime('%Y%m%d')}.csv",
    "text/csv"
)