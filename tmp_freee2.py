
import sys, json, requests
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")
from token_manager import get_headers

COMPANY_ID = 11712776
BASE = "https://api.freee.co.jp/api/1"

# ステータス指定なし・全件
for status in ["submitted", "unsubmitted", "draft", ""]:
    params = {"company_id": COMPANY_ID, "limit": 100}
    if status:
        params["invoice_status"] = status
    res = requests.get(f"{BASE}/invoices", headers=get_headers(), params=params)
    data = res.json()
    count = len(data.get("invoices", []))
    if count > 0 or not status:
        print(f"status={status or 'ALL'}: {count}件 / HTTP{res.status_code}")
        if count > 0:
            for inv in data["invoices"][:3]:
                print(f"  {inv.get('issue_date')} {inv.get('title','')[:30]} {inv.get('total_amount',0):,}")
        elif res.status_code != 200:
            print(f"  エラー: {res.text[:200]}")
