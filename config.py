import os
from datetime import datetime

# Email Configuration
EMAIL_SENDER    = "ypanchia@gmail.com"
EMAIL_PASSWORD  = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVERS = [
    "yeshiel@dailymaverick.co.za"
]
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT   = 587

# Design Constants
THEME = {
    "background": "#FFFFFF",
    "text":       "#1D1D1B",
    "header":     "#005782",
    "positive":   "#008000",
    "negative":   "#FF0000"
}

# Font Configuration
# Make sure you have 'fonts/Georgia.ttf' and 'fonts/GeorgiaBold.ttf' in your repo root
FONT_PATHS = {
    "georgia":      os.path.join(os.getcwd(), "fonts", "Georgia.ttf"),
    "georgia_bold": os.path.join(os.getcwd(), "fonts", "GeorgiaBold.ttf")
}

# Report Layout (520px width)
REPORT_COLUMNS = [
    ("Metric", 160),
    ("Today",  120),
    ("1D%",     70),
    ("1M%",     70),
    ("YTD%",    70)
]

# Data Validation — top‑10 cryptos only
REQUIRED_KEYS = [
    "BTCZAR", "ETHZAR", "BNBZAR", "XRPZAR", "ADAZAR",
    "SOLZAR", "DOGEZAR", "DOTZAR", "TRXZAR", "LTCZAR"
]

def validate_data(data):
    missing = [key for key in REQUIRED_KEYS if key not in data]
    if missing:
        raise ValueError(f"Missing data keys: {', '.join(missing)}")
    return True
