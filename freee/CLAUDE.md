# CLAUDE.md - freee invoice API migration (work rules for Codex)

## Scope (ONLY this)
- Edit freee_invoice_v2.py: migrate INVOICE CREATION from the deprecated freee accounting API
  (POST /api/1/invoices, now returns 404) to the freee Invoice API (POST /iv/invoices).
- Add CLI flags --dry-run and --limit N (see SPEC.md).

## HARD PROHIBITIONS (critical - this script bills real clients)
- DO NOT execute any HTTP POST/PUT/DELETE. DO NOT create, send, or modify any invoice or partner in freee.
- DO NOT run freee_invoice_v2.py except `python -m py_compile freee_invoice_v2.py`. Never run it in create mode.
- DO NOT change amount/profit calc, get_or_create_partner business logic, the Excel data source, or auto_status_update.
- DO NOT edit any file other than freee_invoice_v2.py (and check off TASKS.md).
- Preserve all existing behavior except the invoice POST endpoint+payload and the new flags.

## Verification
- After edits: `python -m py_compile freee_invoice_v2.py` MUST pass.
- Do NOT verify by calling the freee API. Jobz will run the controlled test.

## Done = code edited per SPEC.md + py_compile clean + TASKS.md checked off. Nothing executed against freee.
