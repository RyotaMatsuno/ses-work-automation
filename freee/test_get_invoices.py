import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")

import requests
from token_manager import get_headers

FREEE_BASE = "https://api.freee.co.jp/api/1"
COMPANY_ID = 11712776
h = {**get_headers(), "Content-Type": "application/json"}

# GET /invoices で既存請求書一覧取得を試みる
print("=== GET /invoices ===")
r = requests.get(f"{FREEE_BASE}/invoices", headers=h, params={"company_id": COMPANY_ID, "limit": 1})
print(f"status: {r.status_code}")
print(f"response: {r.text[:500]}")

# GET /me でアクセス可能な会社ID確認
print("\n=== GET /users/me ===")
r2 = requests.get("https://api.freee.co.jp/api/1/users/me", headers=h)
print(f"status: {r2.status_code}")
if r2.status_code == 200:
    data = r2.json()
    companies = data.get("user", {}).get("companies", [])
    for c in companies:
        print(f"  company_id={c.get('id')} name={c.get('display_name')} role={c.get('role')}")
else:
    print(f"response: {r2.text[:300]}")
