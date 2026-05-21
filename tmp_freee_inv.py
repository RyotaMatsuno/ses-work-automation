import sys, requests, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")
from token_manager import get_headers

FREEE_BASE = "https://api.freee.co.jp/api/1"
COMPANY_ID = 11712776

def h():
    hd = get_headers()
    hd["Content-Type"] = "application/json"
    return hd

# 最近の請求書を全件取得
res = requests.get(f"{FREEE_BASE}/invoices",
    headers=h(),
    params={"company_id": COMPANY_ID, "limit": 30, "offset": 0})

invoices = res.json().get("invoices", [])
print(f"請求書件数: {len(invoices)}")
print()

for inv in sorted(invoices, key=lambda x: x.get("due_date",""), reverse=False):
    inv_id = inv.get("invoice_number","")
    partner = inv.get("partner_name","")
    issue = inv.get("issue_date","")
    due = inv.get("due_date","")
    total_exc = inv.get("total_amount_with_vat", 0) // 11 * 10  # 税抜概算
    total_inc = inv.get("total_amount_with_vat", 0)
    status = inv.get("invoice_status","")
    title = inv.get("title","")
    
    # 明細の合計（税抜）
    lines = inv.get("invoice_lines", [])
    line_total = sum(l.get("amount",0) for l in lines)
    
    print(f"[{inv_id}] {partner}")
    print(f"  title: {title}")
    print(f"  請求日:{issue} / 入金期日:{due} / ステータス:{status}")
    print(f"  明細合計(税抜):{line_total:,}円 / 税込:{total_inc:,}円")
    print()
