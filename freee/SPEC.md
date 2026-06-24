# SPEC - freee invoice creation migration to freee Invoice API (/iv)

## Verified facts (live GET-only probe, 2026-06-08)
- Invoice CREATE endpoint: POST https://api.freee.co.jp/iv/invoices  (base path is /iv)
- Token already has the freee Invoice scope (GET /iv/invoices returned 200 JSON). No re-auth needed.
- Required template_id = 3323260  (the only template, name: layout1/classic). From GET /iv/invoices/templates.
- Partners stay on the accounting API: GET/POST https://api.freee.co.jp/api/1/partners (UNCHANGED).
- The accounting API POST /api/1/invoices is DEPRECATED -> 404. This is the root-cause bug.

## Target create payload (derived from GET /iv/invoices/{id} real structure)
Top-level:
- company_id (int) = 11712776
- partner_id (int)              # from get_or_create_partner (keep using /api/1/partners)
- template_id (int) = 3323260
- billing_date (str YYYY-MM-DD)     # replaces old issue_date
- payment_date (str YYYY-MM-DD)     # replaces old due_date
- subject (str)
- payment_type = "transfer"
- tax_entry_method = "out"
- sending_status = "unsent"         # IMPORTANT: create as UNSENT. Never auto-send to clients.
- lines: list of line objects, each:
    - type = "item"                 # replaces old "normal"
    - description (str)             # replaces old line "name"
    - quantity (number)
    - unit (str) = ""
    - unit_price (number or numeric string)
    - tax_rate (int) = 10           # replaces old tax_code
    - reduced_tax_rate (bool) = false
    - withholding (bool)            # SEE T5 - leave configurable, default False, do NOT change amounts

## Field mapping old -> new (inside create_invoice)
- endpoint {FREEE_BASE}/invoices (api/1)  ->  {FREEE_BASE_INV}/invoices  where FREEE_BASE_INV = "https://api.freee.co.jp/iv"
- "invoice_lines" -> "lines"
- line "name" -> "description"
- line "tax_code":1 -> "tax_rate":10 and "reduced_tax_rate":false
- line "type":"normal" -> "type":"item"
- "issue_date" -> "billing_date" ; "due_date" -> "payment_date"
- add "template_id": TEMPLATE_ID, "payment_type":"transfer", "tax_entry_method":"out", "sending_status":"unsent"
- remove "invoice_status"
- success: invoice id at res.json()["invoice"]["id"]. Keep current OK/NG print format and return value.

## Constants to add near FREEE_BASE
FREEE_BASE_ACCT = "https://api.freee.co.jp/api/1"
FREEE_BASE_INV  = "https://api.freee.co.jp/iv"
TEMPLATE_ID = 3323260
# keep FREEE_BASE = FREEE_BASE_ACCT  (partners / backward compat)

## CLI flags (add to run()/__main__)
- --dry-run : build and print each invoice payload as JSON; DO NOT POST. In dry-run, get_or_create_partner
              must NOT create partners (GET/lookup only; if not found, print [DRY] partner-missing:<name> and
              use partner_id=0 placeholder). 
- --limit N : process only the first N target entries.
- Keep the existing positional YYYY-MM target-month argument working alongside the flags.
- Default (no --dry-run): real create (preserve monthly behavior). Jobz controls execution; do NOT run it.

## Out of scope (DO NOT change)
- amount/profit rules, Excel loading, auto_status_update, partner business logic.
