# TASKS.md - backfill_engineers

## Implementation Checklist

- [x] TASK-1: Setup - import dotenv, requests, re, time; load .env; define DB_ID and headers
- [x] TASK-2: fetch_target_records() - query Notion DB with filter (all 3 fields empty), paginate to get all results
- [x] TASK-3: parse_sender() - implement email + person_name extraction from 送信元 line per SPEC
- [x] TASK-4: generate_initial() - implement イニシャル logic per SPEC (handle existing initials, Japanese names, codes)
- [x] TASK-5: build_patch_payload() - build Notion PATCH body with only non-None fields
- [x] TASK-6: patch_notion_page() - PATCH to Notion API with 0.3s sleep, return success/error
- [x] TASK-7: main() - loop over records, call parse/generate/patch, log each result
- [x] TASK-8: write summary to backfill_log.txt (total/updated/skipped/errors)
- [x] TASK-9: dry_run mode - add --dry-run flag that prints planned changes without calling PATCH
- [x] TASK-10: test with first 3 records in dry-run mode, verify output format
