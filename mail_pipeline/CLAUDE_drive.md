# CLAUDE.md - drive_uploader

## Rules
- Edit only files in ses_work/mail_pipeline/ and ses_work/matching_v2/
- Do NOT touch config/.env or config/service_account.json
- Do NOT delete or rename existing functions
- Keep all changes backward compatible (no attachment = existing behavior unchanged)
- Test with dry_run=True before writing to Notion/Drive
- All new code must handle exceptions gracefully (log and continue, never crash pipeline)

## Forbidden
- Do not refactor existing functions
- Do not change function signatures (only add optional parameters)
- Do not import heavy libraries at module top level (use lazy import inside functions)
