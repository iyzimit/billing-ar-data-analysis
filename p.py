import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load your cleaned billing data
df = pd.read_excel(r"C:\Users\ibrahim.zimit\Desktop\billing-ar-analysis\data\final.xlsx")  # use your cleaned file

st.title("Billing Dashboard 💻") 

st.title("💻 Billing Intelligence Dashboard")

# -------------------------------
# KPI Metrics
# -------------------------------
 
total_billed = df['bill_amount'].sum()
total_payments = df['previous_payments'].sum()
total_debt = df['closing_balance'].sum()

st.subheader("📊 Key Metrics")
st.metric("Total Billed ", total_billed)
st.metric("Total Payments", total_payments)
st.metric("Total Outstanding Balance", total_debt)

# -------------------------------
# Payment Percent
# -------------------------------
df.loc[:, 'payment_percent'] = (df['previous_payments'] / df['bill_amount']) * 100

# -------------------------------
# Risk Classification
# -------------------------------
def risk_flag(row):
    if row['payment_percent'] < 20 and row['closing_balance'] > 50000:
        return 'High Risk'
    elif row['payment_percent'] < 50:
        return 'Medium Risk'
    else:
        return 'Low Risk'

df['risk'] = df.apply(risk_flag, axis=1)

# -------------------------------
# Outlier Detection
# -------------------------------
df['z_score'] = (df['bill_amount'] - df['bill_amount'].mean()) / df['bill_amount'].std()
outliers = df[np.abs(df['z_score']) > 2]

# -------------------------------
# Payment Status Filter
# -------------------------------
status_option = st.selectbox(
    "Select Payment Status", 
    ["All", "Low (<20%)", "Medium (20-50%)", "High (>50%)"]
)

if status_option == "Low (<20%)":
    filtered = df[df['payment_percent'] < 20]
elif status_option == "Medium (20-50%)":
    filtered = df[(df['payment_percent'] >= 20) & (df['payment_percent'] <= 50)]
elif status_option == "High (>50%)":
    filtered = df[df['payment_percent'] > 50]
else:
    filtered = df.copy()

st.subheader(f"📋 Customer List: {status_option}")
st.dataframe(filtered[['account_number','bill_amount','previous_payments','payment_percent','closing_balance','risk']])

# -------------------------------
# Bar Chart: Payment Percent
# -------------------------------
st.subheader("📊 Payment Percentage by Customer")
fig, ax = plt.subplots(figsize=(10,5))
bars = ax.bar(filtered['account_number'], filtered['payment_percent'], color='orange')

# Highlight zero payers in red
for bar, percent in zip(bars, filtered['payment_percent']):
    if percent == 0:
        bar.set_color('red')

plt.xticks(rotation=75)
plt.ylabel("Payment Percentage (%)")
st.pyplot(fig)

# -------------------------------
# High-Risk Customers
# -------------------------------
st.subheader("⚠️ High-Risk Customers")
high_risk = df[df['risk'] == 'High Risk']
st.dataframe(high_risk[['account_number','bill_amount','previous_payments','closing_balance','payment_percent']])

# -------------------------------
# Outlier Bills
# -------------------------------
st.subheader("💡 Outlier Bills (Z-Score > 2)")
st.dataframe(outliers[['account_number','bill_amount','z_score']])

# -------------------------------
# Payment Heatmap
# -------------------------------
st.subheader("🔥 Payment & Balance Heatmap")
plt.figure(figsize=(10,6))
sns.heatmap(df[['bill_amount','previous_payments','payment_percent','closing_balance']], 
            annot=True, fmt=".0f", cmap="YlOrRd")
st.pyplot(plt)