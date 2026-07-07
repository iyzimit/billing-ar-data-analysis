# utils.py
import streamlit as st
import pandas as pd
import numpy as np
import time
from config import DATA_PATH, RISK_THRESHOLDS, OUTLIER_Z_THRESHOLD, OPERATIONAL_DATA, NERC_TARGETS
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.units import inch
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io

@st.cache_data
def load_data(filepath=DATA_PATH):
    start = time.time()
    df = pd.read_parquet(filepath, engine='pyarrow')
    load_time = time.time() - start
    return df, load_time

def get_outliers(df, z_threshold=OUTLIER_Z_THRESHOLD):
    return df[np.abs(df['z_score']) > z_threshold]

def filter_by_payment_status(df, status_option):
    if status_option == "Low (<20%)":
        return df[df['payment_percent'] < RISK_THRESHOLDS['high_risk_payment_pct']]
    elif status_option == "Medium (20-50%)":
        return df[(df['payment_percent'] >= RISK_THRESHOLDS['high_risk_payment_pct']) & 
                  (df['payment_percent'] <= RISK_THRESHOLDS['medium_risk_payment_pct'])]
    elif status_option == "High (>50%)":
        return df[df['payment_percent'] > RISK_THRESHOLDS['medium_risk_payment_pct']]
    else:
        return df.copy()

def filter_by_risk(df, risk_list):
    return df[df['risk'].isin(risk_list)]

def get_kpis(df):
    return {
        'total_energy': df['consumption'].sum() if 'consumption' in df.columns else 0,
        'total_billed': df['bill_amount'].sum(),
        'total_payments': df['previous_payments'].sum(),
        'total_debt': df['closing_balance'].sum(),
        'payment_rate': df['previous_payments'].sum() / df['bill_amount'].sum() * 100 if df['bill_amount'].sum() > 0 else 0
    }

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
    
    top_customers = _df.nlargest(50, 'closing_balance')[
        ['account_number','feeder', 'tariff', 'consumption','bill_amount', 'previous_payments', 'closing_balance', 'risk']
    ]
    
    return summary_by_feeder, summary_by_tariff, summary_by_bill_style, summary_by_type, top_customers

def calculate_nerc_metrics(_df):
    """Calculate NERC KPIs for compliance reporting"""
    
    energy_received = OPERATIONAL_DATA['energy_received_kwh']
    energy_billed = _df['consumption'].sum() if 'consumption' in _df.columns else 0
    revenue_billed = _df['bill_amount'].sum()
    revenue_collected = _df['previous_payments'].sum()
    
    billing_efficiency = (energy_billed / energy_received * 100) if energy_received > 0 else 0
    collection_efficiency = (revenue_collected / revenue_billed * 100) if revenue_billed > 0 else 0
    atcc_losses = 100 - (billing_efficiency * collection_efficiency / 100)
    
    billing_ok = billing_efficiency >= NERC_TARGETS['billing_efficiency']
    collection_ok = collection_efficiency >= NERC_TARGETS['collection_efficiency']
    atcc_ok = atcc_losses <= NERC_TARGETS['atcc_target']
    
    return {
        'energy_received': energy_received,
        'energy_billed': energy_billed,
        'revenue_billed': revenue_billed,
        'revenue_collected': revenue_collected,
        'billing_efficiency': billing_efficiency,
        'collection_efficiency': collection_efficiency,
        'atcc_losses': atcc_losses,
        'billing_ok': billing_ok,
        'collection_ok': collection_ok,
        'atcc_ok': atcc_ok,
        'overall_compliant': billing_ok and collection_ok and atcc_ok
    }

 
def generate_nerc_pdf_report(df, nerc_metrics, period_str, logo_path=None):
    """Generate ZIMICO NERC compliance PDF report"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#003366'),
        spaceAfter=12
    )
    
    # Header
    elements.append(Paragraph("Kano Electricity Distribution Company", title_style))
    elements.append(Paragraph("NERC Compliance Report", styles['Heading2']))
    elements.append(Paragraph(f"Reporting Period: {period_str}", styles['Normal']))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Compliance status
    status = "COMPLIANT" if nerc_metrics['overall_compliant'] else "NON-COMPLIANT"
    status_color = colors.green if nerc_metrics['overall_compliant'] else colors.red
    elements.append(Paragraph(f"<b>Overall Status: <font color='{status_color.hexval()}'>{status}</font></b>", styles['Heading3']))
    elements.append(Spacer(1, 0.2*inch))
    
    # NERC KPIs Table
    elements.append(Paragraph("NERC Key Performance Indicators", styles['Heading3']))
    nerc_data = [
        ['Metric', 'Value', 'Target', 'Status'],
        ['Billing Efficiency', f"{nerc_metrics['billing_efficiency']:.1f}%", '≥90%', 'Pass' if nerc_metrics['billing_ok'] else 'Fail'],
        ['Collection Efficiency', f"{nerc_metrics['collection_efficiency']:.1f}%", '≥85%', 'Pass' if nerc_metrics['collection_ok'] else 'Fail'],
        ['ATC&C Losses', f"{nerc_metrics['atcc_losses']:.1f}%", '≤25%', 'Pass' if nerc_metrics['atcc_ok'] else 'Fail']
    ]
    
    t = Table(nerc_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.3*inch))
    
    # Summary stats
    elements.append(Paragraph("Financial Summary", styles['Heading3']))
    summary_data = [
        ['Total Energy Billed (kWh)', f"{nerc_metrics['energy_billed']:,.0f}"],
        ['Total Revenue Billed (₦)', f"{nerc_metrics['revenue_billed']:,.0f}"],
        ['Total Revenue Collected (₦)', f"{nerc_metrics['revenue_collected']:,.0f}"],
        ['Outstanding Balance (₦)', f"{df['closing_balance'].sum():,.0f}"],
        ['Total Customers', f"{len(df):,}"]
    ]
    
    t2 = Table(summary_data, colWidths=[3*inch, 3*inch])
    t2.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
    ]))
    elements.append(t2)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_revenue_alerts(df, config):
    """Generate revenue protection alerts for ZIMICO"""
    alerts = []
    
    # Alert 1: Zero payments + high consumption
    zero_pay_high_cons = df[
        (df['payment_percent'] == 0) & 
        (df['consumption'] > df['consumption'].quantile(0.75)) &
        (df['closing_balance'] > 10000)
    ].copy()
    
    if len(zero_pay_high_cons) > 0:
        alerts.append({
            'type': 'ZERO_PAYMENT_HIGH_CONSUMPTION',
            'severity': 'CRITICAL',
            'count': len(zero_pay_high_cons),
            'total_at_risk': zero_pay_high_cons['closing_balance'].sum(),
            'accounts': zero_pay_high_cons[['account_number', 'feeder', 'consumption', 'closing_balance']].head(20).to_dict('records')
        })
    
    # Alert 2: Sudden bill drop - possible meter bypass
    df['avg_bill'] = df.groupby('account_number')['bill_amount'].transform('mean')
    bill_drop = df[
        (df['bill_amount'] < df['avg_bill'] * 0.3) &  # 70% drop
        (df['consumption'] > df['avg_bill'] / 50) &  # But still consuming
        (df['bill_amount'] > 0)
    ].copy()
    
    if len(bill_drop) > 0:
        alerts.append({
            'type': 'POSSIBLE_METER_BYPASS',
            'severity': 'HIGH',
            'count': len(bill_drop),
            'total_at_risk': bill_drop['bill_amount'].sum(),
            'accounts': bill_drop[['account_number', 'feeder', 'bill_amount', 'consumption']].head(20).to_dict('records')
        })
    
    # Alert 3: Long-term defaulters
    long_defaulters = df[
        (df['payment_percent'] < 10) &
        (df['closing_balance'] > 50000) &
        (df['risk'] == 'High Risk')
    ].copy()
    
    if len(long_defaulters) > 0:
        alerts.append({
            'type': 'LONG_TERM_DEFAULTERS',
            'severity': 'HIGH',
            'count': len(long_defaulters),
            'total_at_risk': long_defaulters['closing_balance'].sum(),
            'accounts': long_defaulters[['account_number', 'feeder', 'closing_balance', 'payment_percent']].head(20).to_dict('records')
        })
    
    # Alert 4: Major feeder underperformance
    if 'feeder' in df.columns:
        feeder_perf = df.groupby('feeder').agg({
            'bill_amount': 'sum',
            'previous_payments': 'sum',
            'account_number': 'count'
        }).reset_index()
        feeder_perf['collection_pct'] = (feeder_perf['previous_payments'] / feeder_perf['bill_amount'] * 100).fillna(0)
        
        major_underperform = feeder_perf[
            (feeder_perf['feeder'].isin(config.get('MAJOR_FEEDERS', []))) &
            (feeder_perf['collection_pct'] < 60)
        ].copy()
        
        if len(major_underperform) > 0:
            alerts.append({
                'type': 'MAJOR_FEEDER_UNDERPAYMENT',
                'severity': 'CRITICAL',
                'count': len(major_underperform),
                'total_at_risk': major_underperform['bill_amount'].sum() - major_underperform['previous_payments'].sum(),
                'accounts': major_underperform.to_dict('records')
            })
    
    return alerts

def format_alert_email(alerts, company_name):
    """Format alerts into email text"""
    if not alerts:
        return f"{company_name} Revenue Protection - No alerts detected. All clear."
    
    total_at_risk = sum(a['total_at_risk'] for a in alerts)
    
    email = f"""
{company_name} - DAILY REVENUE PROTECTION ALERT
Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}

SUMMARY: {len(alerts)} alert types triggered
TOTAL REVENUE AT RISK: ₦{total_at_risk:,.0f}

"""
    
    for alert in alerts:
        email += f"\n{'='*60}\n"
        email += f"ALERT: {alert['type']}\n"
        email += f"Severity: {alert['severity']}\n"
        email += f"Accounts Flagged: {alert['count']}\n"
        email += f"Amount at Risk: ₦{alert['total_at_risk']:,.0f}\n"
        email += f"{'='*60}\n\n"
        
        email += "Top Accounts:\n"
        for acc in alert['accounts'][:10]:
            if 'account_number' in acc:
                email += f"- {acc['account_number']} | {acc.get('feeder', 'N/A')} | ₦{acc.get('closing_balance', acc.get('bill_amount', 0)):,.0f}\n"
        
        email += "\n"
    
    email += "\nAction Required: Review flagged accounts and deploy field teams for verification.\n"
    email += f"\n{company_name} Revenue Protection Department"
    
    return email


def generate_revenue_alerts(df, config):
    """Generate revenue protection alerts for ZIMICO"""
    alerts = []
    
    # Alert 1: Zero payments + high consumption
    zero_pay_high_cons = df[
        (df['payment_percent'] == 0) & 
        (df['consumption'] > df['consumption'].quantile(0.75)) &
        (df['closing_balance'] > 10000)
    ].copy()
    
    if len(zero_pay_high_cons) > 0:
        alerts.append({
            'type': 'ZERO_PAYMENT_HIGH_CONSUMPTION',
            'severity': 'CRITICAL',
            'count': len(zero_pay_high_cons),
            'total_at_risk': zero_pay_high_cons['closing_balance'].sum(),
            'accounts': zero_pay_high_cons[['account_number', 'feeder', 'consumption', 'closing_balance']].head(20).to_dict('records')
        })
    
    # Alert 2: Sudden bill drop - possible meter bypass
    df['avg_bill'] = df.groupby('account_number')['bill_amount'].transform('mean')
    bill_drop = df[
        (df['bill_amount'] < df['avg_bill'] * 0.3) &  # 70% drop
        (df['consumption'] > df['avg_bill'] / 50) &  # But still consuming
        (df['bill_amount'] > 0)
    ].copy()
    
    if len(bill_drop) > 0:
        alerts.append({
            'type': 'POSSIBLE_METER_BYPASS',
            'severity': 'HIGH',
            'count': len(bill_drop),
            'total_at_risk': bill_drop['bill_amount'].sum(),
            'accounts': bill_drop[['account_number', 'feeder', 'bill_amount', 'consumption']].head(20).to_dict('records')
        })
    
    # Alert 3: Long-term defaulters
    long_defaulters = df[
        (df['payment_percent'] < 10) &
        (df['closing_balance'] > 50000) &
        (df['risk'] == 'High Risk')
    ].copy()
    
    if len(long_defaulters) > 0:
        alerts.append({
            'type': 'LONG_TERM_DEFAULTERS',
            'severity': 'HIGH',
            'count': len(long_defaulters),
            'total_at_risk': long_defaulters['closing_balance'].sum(),
            'accounts': long_defaulters[['account_number', 'feeder', 'closing_balance', 'payment_percent']].head(20).to_dict('records')
        })
    
    # Alert 4: Major feeder underperformance
    if 'feeder' in df.columns:
        feeder_perf = df.groupby('feeder').agg({
            'bill_amount': 'sum',
            'previous_payments': 'sum',
            'account_number': 'count'
        }).reset_index()
        feeder_perf['collection_pct'] = (feeder_perf['previous_payments'] / feeder_perf['bill_amount'] * 100).fillna(0)
        
        major_underperform = feeder_perf[
            (feeder_perf['feeder'].isin(config.get('MAJOR_FEEDERS', []))) &
            (feeder_perf['collection_pct'] < 60)
        ].copy()
        
        if len(major_underperform) > 0:
            alerts.append({
                'type': 'MAJOR_FEEDER_UNDERPAYMENT',
                'severity': 'CRITICAL',
                'count': len(major_underperform),
                'total_at_risk': major_underperform['bill_amount'].sum() - major_underperform['previous_payments'].sum(),
                'accounts': major_underperform.to_dict('records')
            })
    
    return alerts

def format_alert_email(alerts, company_name):
    """Format alerts into email text"""
    if not alerts:
        return f"{company_name} Revenue Protection - No alerts detected. All clear."
    
    total_at_risk = sum(a['total_at_risk'] for a in alerts)
    
    email = f"""
{company_name} - DAILY REVENUE PROTECTION ALERT
Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}

SUMMARY: {len(alerts)} alert types triggered
TOTAL REVENUE AT RISK: ₦{total_at_risk:,.0f}

"""
    
    for alert in alerts:
        email += f"\n{'='*60}\n"
        email += f"ALERT: {alert['type']}\n"
        email += f"Severity: {alert['severity']}\n"
        email += f"Accounts Flagged: {alert['count']}\n"
        email += f"Amount at Risk: ₦{alert['total_at_risk']:,.0f}\n"
        email += f"{'='*60}\n\n"
        
        email += "Top Accounts:\n"
        for acc in alert['accounts'][:10]:
            if 'account_number' in acc:
                email += f"- {acc['account_number']} | {acc.get('feeder', 'N/A')} | ₦{acc.get('closing_balance', acc.get('bill_amount', 0)):,.0f}\n"
        
        email += "\n"
    
    email += "\nAction Required: Review flagged accounts and deploy field teams for verification.\n"
    email += f"\n{company_name} Revenue Protection Department"
    
    return email