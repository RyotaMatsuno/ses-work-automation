# Investigation: .env Mismatch + Price Anomaly
Date: 2026-06-19

## .env Audit Results
- 26 vars read in code but not in .env
- High-risk (added to .env): IMAP_HOST/PORT, FREEE/SHEETS_WRITE_APPROVED, SKIP_NOTION_FETCH, LLM_MODEL, MATCH_MODEL
- Already aliased: NOTION_TOKEN (=NOTION_API_KEY), PROJECT_DB_ID (=NOTION_PROJECT_DB_ID), ENGINEER_DB_ID (=NOTION_ENGINEER_DB_ID)
- Safe to ignore: PORT, CLOUD_RUN_URL, RENDER_EXTERNAL_URL
- LINE_BRIDGE_* vars: Cloud Run specific, not needed in local .env

## Price Anomaly Results
- 210 projects with price, 16 anomalies (7.6%)
- Pattern A (0.16-0.40万): daily/hourly rate misinterpreted as monthly
- Pattern B (1.50万): daily rate
- Pattern C (2.27万): person info as project
- Pattern D (300-900万): annual salary / multi-person / team budget

## Recommended Fix (Future Cursor Task)
- Price validation in register_project: flag <15万 or >200万 as suspicious
- Unit-aware normalization (日給→月額 ×20)
- Store raw price text separately from normalized
- Person/project classification guard

## reclass starvation fix
- fetch_unprocessed_from_db updated to 2-query split (fresh 80% / other 20%)
- other 402件 should start processing next pipeline run
