import sys, requests
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")
from token_manager import get_headers

FREEE_BASE = "https://api.freee.co.jp/api/1"
COMPANY_ID = 11712776
h = get_headers()

# ステータス指定なしで全取得
for status in ["draft", "issue", "sent", "unconfirmed", "confirmed"]:
    res = requests.get(f"{FREEE_BASE}/invoices",
        headers=h,
        params={"company_id": COMPANY_ID, "invoice_status": status, "limit": 20})
    data = res.json()
    invs = data.get("invoices", [])
    if invs:
        print(f"\n[{status}] {len(invs)}件")
        for inv in invs:
            lines = inv.get("invoice_lines", [])
            total = sum(l.get("amount",0) for l in lines)
            print(f"  {inv['invoice_number']} / {inv['partner_name']} / 入金期日:{inv.get('due_date','')} / {total:,}円(税抜)")
    else:
        print(f"[{status}] 0件")
