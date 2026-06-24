import sys

import requests

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")
from token_manager import get_headers

headers = get_headers()
company_id = 11712776

# 会社情報取得
r = requests.get(f"https://api.freee.co.jp/api/1/companies/{company_id}", headers=headers, timeout=15)
print(f"company: {r.status_code}")
if r.status_code == 200:
    print(f"  name: {r.json().get('company', {}).get('display_name', '')}")

# 取引先一覧（最初の3件）
r2 = requests.get(
    f"https://api.freee.co.jp/api/1/partners?company_id={company_id}&limit=3", headers=headers, timeout=15
)
print(f"partners: {r2.status_code} ({len(r2.json().get('partners', []))}件)")

# 請求書一覧（最初の3件）
r3 = requests.get(
    f"https://api.freee.co.jp/api/1/invoices?company_id={company_id}&limit=3", headers=headers, timeout=15
)
print(f"invoices: {r3.status_code} ({len(r3.json().get('invoices', []))}件)")
if r3.status_code == 200:
    for inv in r3.json().get("invoices", []):
        print(f"  - {inv.get('invoice_number')} {inv.get('partner_name')} {inv.get('total_amount')}円")
