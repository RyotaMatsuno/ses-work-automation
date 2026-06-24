import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")
import json
from datetime import date

import requests
from dateutil.relativedelta import relativedelta
from token_manager import get_headers

FREEE_BASE = "https://api.freee.co.jp/api/1"
COMPANY_ID = 11712776

h = {**get_headers(), "Content-Type": "application/json"}

# テスト用最小payloadで請求書ドラフト作成
today = date.today()
issue_date = today.replace(day=1)
due_date = issue_date + relativedelta(months=1, days=-1)

payload = {
    "company_id": COMPANY_ID,
    "issue_date": issue_date.strftime("%Y-%m-%d"),
    "due_date": due_date.strftime("%Y-%m-%d"),
    "partner_id": 91256138,  # 株式会社TERRA
    "invoice_status": "draft",
    "title": "テスト請求書",
    "invoice_lines": [{"name": "テスト", "quantity": 1, "unit_price": 15000, "tax_code": 1, "type": "normal"}],
}

print(f"POST {FREEE_BASE}/invoices")
print(f"payload: {json.dumps(payload, ensure_ascii=False)[:300]}")

r = requests.post(f"{FREEE_BASE}/invoices", headers=h, json=payload)
print(f"status: {r.status_code}")
print(f"response: {r.text[:500]}")
