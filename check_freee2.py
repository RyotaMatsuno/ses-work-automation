import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

from freee_auth.token_manager import get_headers

config = dotenv_values(r"config/.env")
company_id = config.get("FREEE_COMPANY_ID", "")
headers = get_headers()

r = requests.get(
    "https://api.freee.co.jp/api/1/invoices", headers=headers, params={"company_id": company_id, "limit": 5}
)
print(f"status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    invoices = data.get("invoices", [])
    print(f"請求書件数: {len(invoices)}")
    for inv in invoices[:3]:
        print(
            f"  id:{inv.get('id')} 宛先:{inv.get('partner_display_name')} ステータス:{inv.get('invoice_status')} 発行日:{inv.get('invoice_date')}"
        )
    # PDFダウンロードAPIを試す
    if invoices:
        inv_id = invoices[0]["id"]
        r2 = requests.get(
            f"https://api.freee.co.jp/api/1/invoices/{inv_id}/download",
            headers=headers,
            params={"company_id": company_id},
        )
        print(f"PDF download status: {r2.status_code} content-type:{r2.headers.get('content-type', '')}")
else:
    print(r.text[:500])
