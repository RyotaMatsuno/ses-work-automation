import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")

import requests
from token_manager import get_headers

FREEE_BASE_INV = "https://api.freee.co.jp/invoice/v1"
COMPANY_ID = 11712776
h = {**get_headers(), "Content-Type": "application/json"}

# GET /invoices で既存データのフィールド構造確認
print("=== GET /invoices ===")
r = requests.get(f"{FREEE_BASE_INV}/invoices", headers=h, params={"company_id": COMPANY_ID, "limit": 3})
print(f"status: {r.status_code}")
print(f"body: {r.text[:1000]}")
