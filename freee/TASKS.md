# TASKS - freee /iv migration (check off as done)
- [!] T1: add FREEE_BASE_INV, FREEE_BASE_ACCT, TEMPLATE_ID constants (keep FREEE_BASE = FREEE_BASE_ACCT) （2026-06-16 GPT-4o判定:NG）
- [!] T2: rewrite create_invoice() payload to the /iv schema (lines/description/tax_rate/billing_date/payment_date/template_id/sending_status=unsent); POST to {FREEE_BASE_INV}/invoices （2026-06-16 GPT-4o判定:NG）
- [!] T3: update success parse to res.json()["invoice"]["id"]; keep OK/NG print + return value （2026-06-16 GPT-4o判定:NG）
- [!] T4: add --dry-run (no POST; partner lookup GET-only, no create) and --limit N flags （2026-06-17 GPT-4o判定:NG）
- [ ] T5: make 'withholding' a single clearly-commented constant (default False). Add TODO: policy unconfirmed by CEO. Do NOT alter amount calculations.
- [ ] T6: python -m py_compile freee_invoice_v2.py  -> must pass
- [ ] T7: DO NOT run against freee. Output a short diff summary of what changed.
