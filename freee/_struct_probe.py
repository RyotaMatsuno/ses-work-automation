import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "freee")
import freee_invoice_v2 as m

B = m.FREEE_BASE_INV
C = m.COMPANY_ID
H = m.freee_headers()
r = requests.get(B + "/invoices", headers=H, params={"company_id": C, "limit": 14, "offset": 92})
invs = r.json().get("invoices") or []
print("=== 直近の請求書 ===")
for i in invs:
    print(
        " id",
        i.get("id"),
        "| partner:",
        i.get("partner_name"),
        "|",
        str(i.get("subject"))[:24],
        "| bill",
        i.get("billing_date"),
        "| pay",
        i.get("payment_date"),
    )
print("=== 明細構造チェック（X月分請求書を最大3件） ===")
seen = 0
for i in invs:
    subj = str(i.get("subject") or "")
    if subj.endswith("請求書") and seen < 3:
        seen += 1
        d = (
            requests.get(B + "/invoices/" + str(i.get("id")), headers=H, params={"company_id": C})
            .json()
            .get("invoice", {})
        )
        lines = d.get("lines") or []
        print(f"-- {d.get('partner_name')} / 件名:{subj} / 明細数={len(lines)} / 合計={d.get('total_amount')}")
        for ln in lines[:8]:
            print(
                "     -", str(ln.get("description"))[:44], "| qty", ln.get("quantity"), "| price", ln.get("unit_price")
            )
