import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import freee_invoice_monthly as M
import requests

dates = M.get_target_dates()
people, warnings = M.load_people(dates["target_month"])
groups = M.group_people(people)
bd = dates["billing_date"].isoformat()
subj = dates["subject"]
hdr = M.freee_headers()

# 既存請求書（当月billing_date×subject一致）を (partner_id,payment_date)->summary で集める
existing = {}
offset = 0
while True:
    r = requests.get(
        f"{M.FREEE_BASE_INV}/invoices", headers=hdr, params={"company_id": M.COMPANY_ID, "limit": 100, "offset": offset}
    )
    invs = r.json().get("invoices") or []
    for inv in invs:
        if inv.get("billing_date") == bd and inv.get("subject") == subj:
            existing[(inv.get("partner_id"), inv.get("payment_date"))] = inv
    if len(invs) < 100:
        break
    offset += 100


def norm(lines):
    out = []
    for l in lines:
        if l.get("type") != "item":
            continue
        q = int(float(l.get("quantity", 1)))
        up = int(float(str(l.get("unit_price", 0)).replace(",", "")))
        out.append((l.get("description"), q, up))
    return sorted(out)


def fetch_inv(inv_id):
    r = requests.get(f"{M.FREEE_BASE_INV}/invoices/{inv_id}", headers=hdr, params={"company_id": M.COMPANY_ID})
    return r.json().get("invoice", {})


grand_gen = 0
for key in sorted(groups, key=lambda k: (k[0], int(k[1]))):
    partner, bk = key
    payload = M.build_payload(partner, bk, groups[key], dates)
    gen = norm(payload["lines"])
    gen_sub = sum(q * up for _, q, up in gen)
    grand_gen += gen_sub
    pid_pd = (payload["partner_id"], payload["payment_date"])
    inv = existing.get(pid_pd)
    if not inv:
        print(f"[NO-MATCH] {partner}/{bk}日 gen_subtotal={gen_sub} 既存なし")
        continue
    full = fetch_inv(inv["id"])
    got = norm(full.get("lines", []))
    got_sub = sum(q * up for _, q, up in got)
    mark = "MATCH" if gen == got else "DIFF"
    print(
        f"[{mark}] {partner}/{bk}日 inv={inv.get('invoice_number')} "
        f"gen_subtotal={gen_sub} inv_subtotal={got_sub} inv_total={inv.get('total_amount')}"
    )
    if gen != got:
        print("   GEN:", gen)
        print("   INV:", got)

print(f"--- GEN grand subtotal(税抜・源泉前) = {grand_gen} ---")
print(f"--- warnings: {len(warnings)} ---")
for w in warnings:
    print("   ", w)
