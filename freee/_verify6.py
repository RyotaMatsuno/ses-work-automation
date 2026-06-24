import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "freee")
import freee_invoice_v2 as m

B = m.FREEE_BASE_INV
C = m.COMPANY_ID
H = m.freee_headers()


def n(v):
    return v if isinstance(v, (int, float)) else 0


ids = {
    "60382177": "GL 30日サイト→30日",
    "60382182": "GL 31-45→45日",
    "60382186": "TERRA 30日→30日(源泉)",
    "60382189": "TERRA 31-45→45日(源泉)",
    "60382190": "TERRA 46以上→46日(源泉)",
    "60382197": "FT 一律45日",
}
print("=== 作成済み6枚 検証 ===")
for iid, label in ids.items():
    d = requests.get(f"{B}/invoices/{iid}", headers=H, params={"company_id": C}).json().get("invoice", {})
    print(f"[{label}] id={iid} No={d.get('invoice_number')}")
    print(
        f"    件名={d.get('subject')} / {d.get('partner_name')} {d.get('partner_title')} / 請求日{d.get('billing_date')} / 支払期限{d.get('payment_date')}"
    )
    print(
        f"    税抜{n(d.get('amount_excluding_tax')):,} 消費税{n(d.get('amount_tax')):,} 源泉{n(d.get('amount_withholding_tax')):,} 合計{n(d.get('total_amount')):,} 状態={d.get('sending_status')} 明細{len(d.get('lines') or [])}行"
    )
