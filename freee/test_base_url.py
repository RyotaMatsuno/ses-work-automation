import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")
import requests
from token_manager import get_headers

h = {**get_headers(), "Content-Type": "application/json"}
COMPANY_ID = 11712776

# freee請求書APIのベースURL候補を試す
base_candidates = [
    "https://invoice.freee.co.jp/api/1",
    "https://api.freee.co.jp/invoice/v1",
    "https://api.freee.co.jp/invoice/api/1",
    "https://iv.freee.co.jp/api/1",
]

for base in base_candidates:
    url = f"{base}/invoices"
    try:
        r = requests.get(url, headers=h, params={"company_id": COMPANY_ID}, timeout=5)
        print(f"GET {url}: {r.status_code}")
    except Exception as e:
        print(f"GET {url}: ERROR {e}")
