import json

import requests

TOKEN_FILE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth\freee_token.json"
COMPANY_ID = 11712776

with open(TOKEN_FILE, encoding="utf-8") as f:
    token_data = json.load(f)

access_token = token_data["access_token"]
headers = {"Authorization": f"Bearer {access_token}"}

# 請求書リスト取得テスト
res = requests.get(f"https://api.freee.co.jp/api/1/invoices?company_id={COMPANY_ID}&limit=5", headers=headers)
print(f"請求書API: status={res.status_code}")
if res.status_code == 200:
    data = res.json()
    invoices = data.get("invoices", [])
    print(f"取得件数: {len(invoices)}")
    for inv in invoices[:3]:
        print(
            f"  {inv.get('invoice_number')} / {inv.get('partner_name')} / {inv.get('total_amount')}円 / {inv.get('invoice_status')}"
        )
else:
    print(f"Error: {res.text[:300]}")
