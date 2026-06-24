import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")

import requests
from token_manager import get_headers

FREEE_BASE = "https://api.freee.co.jp/api/1"
COMPANY_ID = 11712776
h = {**get_headers(), "Content-Type": "application/json"}

# 超最小payload（invoice_lines無し）
payload = {
    "company_id": COMPANY_ID,
    "issue_date": "2026-06-01",
    "due_date": "2026-06-30",
    "partner_id": 91256138,
    "invoice_status": "draft",
}

print("=== 最小payload（lines無し） ===")
r = requests.post(f"{FREEE_BASE}/invoices", headers=h, json=payload)
print(f"status: {r.status_code}")
print(f"response: {r.text[:500]}")

# invoice_lines → invoice_details
payload2 = {
    "company_id": COMPANY_ID,
    "issue_date": "2026-06-01",
    "due_date": "2026-06-30",
    "partner_id": 91256138,
    "invoice_status": "draft",
    "invoice_contents": [
        {
            "order": 1,
            "type": "normal",
            "qty": 1,
            "unit_price": 15000,
            "description": "テスト",
        }
    ],
}

print("\n=== invoice_contents で試す ===")
r2 = requests.post(f"{FREEE_BASE}/invoices", headers=h, json=payload2)
print(f"status: {r2.status_code}")
print(f"response: {r2.text[:500]}")
