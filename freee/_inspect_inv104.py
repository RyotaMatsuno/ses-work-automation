import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import freee_invoice_monthly as M
import requests

r = requests.get(
    f"{M.FREEE_BASE_INV}/invoices/60360044", headers=M.freee_headers(), params={"company_id": M.COMPANY_ID}
)
print("HTTP", r.status_code)
inv = r.json().get("invoice", {})
for k in [
    "id",
    "invoice_number",
    "subject",
    "billing_date",
    "payment_date",
    "total_amount",
    "invoice_status",
    "sending_status",
    "partner_id",
    "partner_name",
]:
    print(f"  {k}: {inv.get(k)}")
print("  lines:")
for l in inv.get("lines", []):
    if l.get("type") == "item":
        print(f"    - {l.get('description')} x{l.get('quantity')} @{l.get('unit_price')}")
