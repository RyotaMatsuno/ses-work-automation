# SPEC.md - backfill_engineers

## Purpose
One-shot script to backfill missing fields in the Notion Engineer DB.
19 records exist, 18 have empty イニシャル/所属メール/所属担当者名.
Source data is in the 備考（LINEメモ）field.

## Input
Notion Engineer DB: 343450ff-37c0-819d-8769-fb0a8a4ceeb1
Filter: イニシャル is empty AND 所属メール is empty AND 所属担当者名 is empty

## 送信元 Parsing Logic

### Email Extraction
From the 備考（LINEメモ）field, find line matching: `送信元:\s*(.+)`
Then extract email from these patterns (in order of priority):
1. `Name <email@domain>` -> email = email@domain
2. `<email@domain>` -> email = email@domain
3. `email@domain` (bare, no angle brackets) -> email = email@domain
4. No match -> leave 所属メール empty

### Person Name Extraction (所属担当者名)
From the same 送信元 line:
1. Pattern `Name(CompanyName)<email>` -> person_name = Name (strip company name in parens)
2. Pattern `Name <email>` -> person_name = Name (everything before `<`)
3. Pattern `CompanyName<email>` -> If it looks like a company (contains katakana or common corp suffixes), person_name = empty
4. Pattern `<email>` only -> person_name = empty
5. Pattern bare email -> person_name = empty

Company detection heuristics (skip name extraction if matched):
- Contains: 株式会社, 合同会社, Inc, Corp, Ltd, LLC, エンジニア, テック, リンク, ソリューション
- All uppercase ASCII (like "PROUD")
- Looks like a domain (no space, contains dot)

### イニシャル Generation
From the 名前 field:
1. If 名前 already matches `^[A-Z]\.[A-Z]$` or `^[A-Z]{2,3}$` -> use as-is (already initials)
2. If 名前 contains spaces (Japanese full name like "川村 俊之"):
   - Split by space
   - For each token, use the romaji initial based on first character reading
   - IMPORTANT: Do NOT attempt kanji-to-romaji conversion (too error-prone)
   - Instead: just use the first character count: "川村 俊之" -> 2 tokens -> format as "??.??" placeholder
   - Actually: skip automatic generation for Japanese names - leave empty and log as "NEEDS_MANUAL"
3. If 名前 is a skill-sheet code (alphanumeric like "174BZ06") -> skip, leave empty, log as "SKIP_CODE"
4. If 名前 is short ASCII (1-3 chars, no dot) like "UT", "OT" -> use as-is

### Special case: 名前 that is already initials
Pattern: matches r'^[A-Z\s\.]{2,6}$' -> treat as existing initials, use as-is

## Update Logic
For each target record:
1. Parse 備考 to extract email and person_name
2. Generate イニシャル from 名前
3. Build PATCH payload with only non-empty derived values
4. PATCH to Notion API
5. Log result: page_id | 名前 | action taken | values set

## Output
- Console log of each record processed
- Summary: total processed / updated / skipped / errors
- Log file: backfill/backfill_log.txt

## Error Handling
- If Notion API returns error, log and continue (do not abort)
- If 送信元 line not found in 備考, log as "NO_SENDER" and skip email/name fields
- If email extraction fails, skip 所属メール update

## Files
- ses_work/backfill/backfill_engineers.py (main script)
- ses_work/backfill/backfill_log.txt (output log)
