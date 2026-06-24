import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")

import requests
from token_manager import get_headers

FREEE_BASE_INV = "https://api.freee.co.jp/invoice/v1"
COMPANY_ID = 11712776
h = {**get_headers(), "Content-Type": "application/json"}

# 1. テンプレート一覧取得（freee請求書API）
print("=== GET /invoices/templates ===")
r = requests.get(f"{FREEE_BASE_INV}/invoices/templates", headers=h, params={"company_id": COMPANY_ID})
print(f"status: {r.status_code}")
if r.status_code == 200:
    tmpl = r.json().get("templates", [])
    for t in tmpl[:3]:
        print(f"  template_id={t.get('id')} name={t.get('name')}")
    first_tmpl_id = tmpl[0]["id"] if tmpl else None
else:
    print(f"response: {r.text[:200]}")
    first_tmpl_id = None

# 2. 請求書GETで既存のフィールド構造を確認
print("\n=== GET /invoices (既存1件確認) ===")
r2 = requests.get(f"{FREEE_BASE_INV}/invoices", headers=h, params={"company_id": COMPANY_ID, "limit": 1})
print(f"status: {r2.status_code}")
if r2.status_code == 200:
    invs = r2.json().get("invoices", [])
    if invs:
        inv = invs[0]
        print(f"  keys: {list(inv.keys())}")
        contents = inv.get("invoice_contents", inv.get("invoice_lines", []))
        if contents:
            print(f"  contents[0] keys: {list(contents[0].keys())}")
