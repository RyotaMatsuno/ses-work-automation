import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")

import requests
from token_manager import get_headers

FREEE_BASE_INV = "https://api.freee.co.jp/invoice/api/1"
COMPANY_ID = 11712776
h = {**get_headers(), "Content-Type": "application/json"}

# GET /invoices の構造確認
print("=== GET /invoices ===")
r = requests.get(f"{FREEE_BASE_INV}/invoices", headers=h, params={"company_id": COMPANY_ID, "limit": 1})
print(f"status: {r.status_code}")
data = r.json()
invs = data.get("invoices", [])
if invs:
    print(f"keys: {list(invs[0].keys())}")
    contents = invs[0].get("invoice_contents", invs[0].get("invoice_lines", []))
    if contents:
        print(f"contents[0] keys: {list(contents[0].keys())}")

# GET /invoices/templates
print("\n=== GET /invoices/templates ===")
rt = requests.get(f"{FREEE_BASE_INV}/invoices/templates", headers=h, params={"company_id": COMPANY_ID})
print(f"status: {rt.status_code}")
print(f"body[:500]: {rt.text[:500]}")

# テンプレートなしPOST試験
print("\n=== POST /invoices (最小) ===")
payload = {
    "company_id": COMPANY_ID,
    "issue_date": "2026-06-01",
    "due_date": "2026-06-30",
    "billing_date": "2026-06-01",
    "invoice_number": "TEST-001",
    "title": "テスト請求書",
    "invoice_contents": [
        {
            "order": 1,
            "type": "normal",
            "qty": "1",
            "unit_price": "15000",
            "description": "テスト明細",
        }
    ],
}
rp = requests.post(f"{FREEE_BASE_INV}/invoices", headers=h, json=payload)
print(f"status: {rp.status_code}")
print(f"response: {rp.text[:600]}")
