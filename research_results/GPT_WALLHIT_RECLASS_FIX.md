# GPT Wall-Hit: Pipeline DB Reclassification Fix
Date: 2026-06-19
Model: gpt-5.4
Effort: low

## Problem
- 1228 unprocessed records in raw_inbox.db (402 other-reset + 826 None)
- Pipeline only processes IMAP-fetched emails, no path to re-process DB-resident records
- Root cause: `new_emails = [e for e in emails if e["msg_id"] not in processed]` uses IMAP as sole work source

## GPT Recommendation (agreed by Jobzu)
1. Replace IMAP-only filtering with DB work queue
2. Keep IMAP fetch + DB insert as-is
3. Add `load_unprocessed_work_items()` query: SELECT WHERE processed=0 ORDER BY NULL-first, other-second
4. Integrate into main loop (NOT separate mode)
5. For other-reset: rule-based reclassification first, skip AI if rule catches as project
6. Split quota: 60 fresh/None + 40 reclass per run (PROCESS_LIMIT=100)

## Cost Optimization
- 402 other records: 55/60 sampled now match by rule → skip AI, go straight to extract
- Only AI-classify leftovers if budget allows
- Expected AI cost savings: ~90% on reclassification batch

## Implementation Priority
1. Process 826 None rows normally
2. Process 402 other-reset with rule-only first
3. AI only on leftovers if budget allows
