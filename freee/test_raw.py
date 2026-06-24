import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")
import requests
from token_manager import get_headers

COMPANY_ID = 11712776
h = {**get_headers(), "Content-Type": "application/json"}

bases = [
    "https://api.freee.co.jp/api/1",
    "https://api.freee.co.jp/invoice/api/1",
]
for base in bases:
    r = requests.get(f"{base}/invoices", headers=h, params={"company_id": COMPANY_ID, "limit": 1})
    print(f"GET {base}/invoices: status={r.status_code} len={len(r.content)}")
    print(f"  Content-Type: {r.headers.get('Content-Type', '')}")
    print(f"  body[:200]: {r.text[:200]}")
    print()
