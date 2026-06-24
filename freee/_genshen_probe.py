import json
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "freee")
import freee_invoice_v2 as m

B = m.FREEE_BASE_INV
C = m.COMPANY_ID
H = m.freee_headers()
# 58800302 = TERRA 4月分（源泉ありのはず）
d = requests.get(B + "/invoices/58800302", headers=H, params={"company_id": C}).json().get("invoice", {})
print("=== TERRA 4月分 源泉表現の確認 ===")
for k in [
    "id",
    "invoice_number",
    "subject",
    "partner_name",
    "partner_title",
    "billing_date",
    "payment_date",
    "tax_entry_method",
    "tax_fraction",
    "withholding_tax_entry_method",
    "amount_excluding_tax",
    "amount_tax",
    "amount_withholding_tax",
    "amount_including_tax",
    "total_amount",
    "sending_status",
]:
    print(f"  {k} = {json.dumps(d.get(k), ensure_ascii=False)}")
print("=== lines ===")
for ln in d.get("lines") or []:
    print(
        "  ",
        json.dumps(
            {
                kk: ln.get(kk)
                for kk in [
                    "type",
                    "description",
                    "quantity",
                    "unit",
                    "unit_price",
                    "tax_rate",
                    "withholding",
                    "amount_excluding_tax",
                ]
            },
            ensure_ascii=False,
        ),
    )
