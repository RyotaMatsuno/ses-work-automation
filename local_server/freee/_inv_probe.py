import io
import json
import sys

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from token_manager import get_headers

BASE_INV = "https://api.freee.co.jp/iv"
COMPANY_ID = 11712776
H = get_headers()

r = requests.get(f"{BASE_INV}/invoices", headers=H, params={"company_id": COMPANY_ID, "limit": 5})
print("LIST status", r.status_code)
data = r.json()
invs = data.get("invoices") or data.get("invoice") or []
print("list count", len(invs))
if not invs:
    print(json.dumps(data, ensure_ascii=False)[:1500])
    sys.exit()

inv_id = invs[0].get("id")
print("first invoice id", inv_id)
r2 = requests.get(f"{BASE_INV}/invoices/{inv_id}", headers=H, params={"company_id": COMPANY_ID})
print("DETAIL status", r2.status_code)
body = r2.json()
d = body.get("invoice", body)
print("--- top-level keys ---")
print(sorted(d.keys()))
TARGET = [
    "tax_fraction",
    "withholding_tax_entry_method",
    "partner_title",
    "tax_entry_method",
    "payment_type",
    "template_id",
    "sending_status",
    "partner_id",
    "invoice_status",
    "booking_date",
    "billing_date",
    "payment_date",
]
print("--- target values (from real existing invoice) ---")
for k in TARGET:
    print(f"  {k} = {json.dumps(d.get(k), ensure_ascii=False)}")
lines = d.get("lines") or []
if lines:
    print("--- line[0] keys ---", sorted(lines[0].keys()))
