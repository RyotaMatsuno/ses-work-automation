
import sys, json, requests
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")
from token_manager import get_headers

COMPANY_ID = 11712776
BASE = "https://api.freee.co.jp/api/1"

# 請求書一覧取得（最新100件）
res = requests.get(f"{BASE}/invoices", headers=get_headers(),
    params={"company_id": COMPANY_ID, "limit": 100})
invoices = res.json().get("invoices", [])

# 人員名でグループ化
out = []
for inv in invoices:
    title = inv.get("title", "")
    issue_date = inv.get("issue_date", "")
    total = inv.get("total_amount", 0)
    status = inv.get("invoice_status", "")
    lines = inv.get("invoice_lines", [])
    line_names = [l.get("name","") for l in lines]
    out.append({
        "id": inv.get("id"),
        "title": title,
        "issue_date": issue_date,
        "total": total,
        "status": status,
        "lines": line_names
    })

with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_invoices.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"請求書: {len(out)}件取得")
# 川崎・齋藤で検索
for inv in out:
    if any(k in inv["title"] for k in ["川崎", "齋藤", "斎藤"]):
        print(f"  HIT: {inv['issue_date']} {inv['title']} {inv['total']:,}円")
