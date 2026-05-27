import requests, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import dotenv_values
from freee_auth.token_manager import get_valid_token

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = get_valid_token()
company_id = config.get('FREEE_COMPANY_ID', '')

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 請求書一覧取得（最新10件）
r = requests.get(
    f"https://api.freee.co.jp/api/1/invoices",
    headers=headers,
    params={"company_id": company_id, "limit": 5, "offset": 0}
)
print(f"status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    invoices = data.get('invoices', [])
    print(f"請求書件数: {len(invoices)}")
    for inv in invoices:
        print(f"  id:{inv.get('id')} 宛先:{inv.get('partner_display_name')} 金額:{inv.get('total_amount')} ステータス:{inv.get('invoice_status')} 発行日:{inv.get('invoice_date')}")
        # PDFダウンロードエンドポイント確認
        print(f"  PDF endpoint: /api/1/invoices/{inv.get('id')}/download")
else:
    print(r.text[:500])
