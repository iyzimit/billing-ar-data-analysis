# config.py - KEDCO Production Config
# Kano Electricity Distribution Company

# -------------------------------
# Branding
# -------------------------------
COMPANY_NAME = "KEDCO Data Systems"
COMPANY_SHORT = "KEDCO"
PAGE_TITLE = "Billing Intelligence Dashboard"
PAGE_ICON = "💻"
AUTHOR = "Ibrahim Zimit"
LOGO_PATH = "C:\\Users\\ibrahim.zimit\\Desktop\\billing-ar-analysis\\assets\\KEDCO_logo.png" 

# -------------------------------
# KEDCO Brand Colors - from official style guide
# -------------------------------
COLORS = {
    'primary': '#003366',      # KEDCO Navy Blue
    'secondary': '#00509E',    # KEDCO Light Blue
    'danger': '#C41E3A',       # Red - zero payments
    'warning': '#FF8C00',      # Orange - low payments  
    'success': '#228B22',      # Green - good collection
    'accent': '#FFD700',       # Gold - highlights
}

RISK_COLORS = {
    'High Risk': COLORS['danger'],
    'Medium Risk': COLORS['warning'],
    'Low Risk': COLORS['success'],
}

# -------------------------------
# File Paths
# -------------------------------
DATA_PATH = "C:\\Users\\ibrahim.zimit\\Desktop\\billing-ar-analysis\\data\\final.parquet"
EXCEL_PATH = "C:\\Users\\ibrahim.zimit\\Desktop\\billing-ar-analysis\\data\\final.xlsx"

# -------------------------------
# KEDCO Business Rules - NERC Approved
# -------------------------------
RISK_THRESHOLDS = {
    'high_risk_payment_pct': 20,      # < 20% paid = high risk
    'high_risk_balance': 50000,       # > ₦50k outstanding = high risk  
    'medium_risk_payment_pct': 50,    # < 50% paid = medium risk
    'disconnection_threshold': 90,     # Days overdue before disconnection
}

OUTLIER_Z_THRESHOLD = 2               # z-score > 2 = outlier bill
COLLECTION_TARGET = 85                # NERC target collection %

# -------------------------------
# KEDCO NERC Tariff Bands 2024
# -------------------------------
TARIFF_BANDS = {
    'A': {'name': 'Band A', 'min_hours': 20, 'desc': '20+ hours/day'},
    'B': {'name': 'Band B', 'min_hours': 16, 'desc': '16-20 hours/day'},
    'C': {'name': 'Band C', 'min_hours': 12, 'desc': '12-16 hours/day'},
    'D': {'name': 'Band D', 'min_hours': 8, 'desc': '8-12 hours/day'},
    'E': {'name': 'Band E', 'min_hours': 4, 'desc': '4-8 hours/day'},
}

# KEDCO Customer Types
CUSTOMER_TYPES = ['Residential', 'Commercial', 'Industrial', 'Special', 'Street Lighting']

# KEDCO Feeders - add your major ones
MAJOR_FEEDERS = [
    'Kumbotso 33KV', 'Dan Agundi 33KV', 'Zaria Road 11KV', 
    'Sabon Gari 11KV', 'Nassarawa 33KV', 'Dakata 11KV'
]
 
DATE_COLUMN = 'period'  

# -------------------------------
# Chart/table limits
# -------------------------------
TOP_N_CUSTOMERS = 20
TOP_N_DEBTORS = 50
HEATMAP_ROWS = 50
TOP_N_FEEDERS = 10

# -------------------------------
# Formatting
# -------------------------------
NAIRA_FORMAT = "₦{:,.0f}"
PERCENT_FORMAT = "{:.1f}%"
KWH_FORMAT = "{:,.0f} kWh"
DATE_FORMAT = '%Y-%m-%d'  

 

# -------------------------------
# NERC Compliance Thresholds
# -------------------------------
NERC_TARGETS = {
    'collection_efficiency': 85,      # NERC minimum 85%
    'billing_efficiency': 90,         # NERC minimum 90%  
    'atcc_target': 25,                # NERC max 25% ATC&C losses
    'disconnection_days': 90,         # Days overdue per NERC order
}

# -------------------------------
# KEDCO Operational Data - update monthly
# -------------------------------
OPERATIONAL_DATA = {
    'energy_received_kwh': 125000000,  # Update: Total energy from TCN monthly
    'reporting_month': 'June 2026',    # Update monthly
    'total_customers': 850000,         # KEDCO customer base
}