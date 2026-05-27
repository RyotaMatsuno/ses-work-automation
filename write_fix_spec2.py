import os

base = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_notify_fix'
os.makedirs(base, exist_ok=True)

claude_md = """# CLAUDE.md - pipeline_notify_fix

## Target files
- ses_work/mail_pipeline/mail_pipeline.py
- ses_work/matching_v2/matching_v2.py
- ses_work/matching_v2/notify_line.py

## Rules
- UTF-8 encoding required
- Do NOT send actual LINE messages (use --dry-run only for testing)
- Do NOT hardcode API keys (read from config/.env)
- Do NOT modify .bak_* files
"""

spec_md = """# SPEC: Full Pipeline Fix

## Fix 1: mail_pipeline.py - Process all emails (no 50-limit)

File: ses_work/mail_pipeline/mail_pipeline.py

### Change constants
```python
# Before
FETCH_LIMIT = 50
PROCESS_LIMIT = 20

# After
FETCH_LIMIT = 500
PROCESS_LIMIT = 500
```

### Change IMAP search in fetch_recent_emails()
Add SINCE-based search so only today's emails are fetched first,
falling back to ALL if today yields nothing.
Keep processed_ids.json diff logic to skip already-processed messages.

```python
def fetch_recent_emails(limit: int = 500):
    log(f"IMAP connecting (up to {limit} emails)")
    # ...existing SSL setup...
    today_str = datetime.now().strftime("%d-%b-%Y")
    status, messages = mail.search(None, f"SINCE {today_str}")
    all_ids = messages[0].split() if status == "OK" and messages[0] else []
    if not all_ids:
        status, messages = mail.search(None, "ALL")
        all_ids = messages[0].split() if status == "OK" and messages[0] else []
    # take last N, newest-first
    target_ids = list(reversed(all_ids[-limit:]))
    log(f"Total: {len(all_ids)} emails -> processing up to {limit}")
    # ...rest unchanged...
```

---

## Fix 2: matching_v2.py - Add raw_body to result.json

File: ses_work/matching_v2/matching_v2.py

In the function that fetches project properties from Notion,
add raw_body extraction:

```python
raw_body = get_text_property(props, "案件詳細") or get_text_property(props, "備考（LINEメモ）") or ""
project["raw_body"] = raw_body
```

Similarly for engineers:
```python
raw_body = get_text_property(props, "備考（LINEメモ）") or ""
engineer["raw_body"] = raw_body
```

The result.json items should include raw_body:
```json
{
  "project_id": "...",
  "project_name": "...",
  "raw_body": "original email/LINE text here",
  "candidates": [
    {
      "engineer_id": "...",
      "raw_body": "original engineer email text",
      ...
    }
  ]
}
```

---

## Fix 3: notify_line.py - Show raw_body in LINE notification

File: ses_work/matching_v2/notify_line.py

### 3a. get_page_info() - add raw_body field

For page_type == "project":
```python
"raw_body": get_first_text_property(props, ["案件詳細", "備考（LINEメモ）"]),
```

For page_type == "engineer":
```python
"raw_body": get_text_property(props, "備考（LINEメモ）"),
```

### 3b. empty_page_info() - add raw_body key
```python
# For both "project" and "engineer":
"raw_body": "",
```

### 3c. main() - pass raw_body from result.json
After fetching project_info from Notion, override with result.json raw_body if Notion value is empty:
```python
if not project_info.get("raw_body"):
    project_info["raw_body"] = item.get("raw_body", "")
```
Similarly for each candidate's engineer_info:
```python
if not engineer_info.get("raw_body"):
    engineer_info["raw_body"] = candidate.get("raw_body", "")
```

### 3d. build_project_message() - append raw_body sections

After the current "意向確認をお願いします。" line, add:

```python
# Project raw_body
proj_raw = project_info.get("raw_body", "").strip()
if proj_raw:
    lines.append("")
    lines.append("【元データ（案件）】")
    preview = proj_raw[:2000]
    lines.append(preview)
    if len(proj_raw) > 2000:
        lines.append(f"... (total {len(proj_raw)} chars, truncated)")

# Engineer raw_body (per candidate)
for item in candidate_infos:
    eng_info = item["engineer_info"]
    eng_raw = eng_info.get("raw_body", "").strip()
    eng_name = eng_info.get("name", "")
    if eng_raw:
        lines.append("")
        lines.append(f"【元データ（{eng_name}）】")
        preview = eng_raw[:1500]
        lines.append(preview)
        if len(eng_raw) > 1500:
            lines.append(f"... (total {len(eng_raw)} chars, truncated)")
```

---

## Completion Criteria

1. mail_pipeline/mail_pipeline.py: FETCH_LIMIT=500, PROCESS_LIMIT=500
2. mail_pipeline/mail_pipeline.py: fetch_recent_emails uses SINCE today search
3. matching_v2/matching_v2.py: result.json items contain "raw_body" field
4. matching_v2/notify_line.py: get_page_info project/engineer include raw_body
5. matching_v2/notify_line.py: empty_page_info includes raw_body key
6. matching_v2/notify_line.py: main() fills raw_body from result.json as fallback
7. matching_v2/notify_line.py: build_project_message() appends raw_body sections
8. python -c "import py_compile; py_compile.compile('mail_pipeline/mail_pipeline.py')" -> no error
9. python -c "import py_compile; py_compile.compile('matching_v2/matching_v2.py')" -> no error
10. python -c "import py_compile; py_compile.compile('matching_v2/notify_line.py')" -> no error
11. python matching_v2/notify_line.py --dry-run -> exits 0, output contains raw_body section
"""

tasks_md = """# TASKS.md - pipeline_notify_fix

- [ ] 1. mail_pipeline.py: change FETCH_LIMIT=500, PROCESS_LIMIT=500
- [ ] 2. mail_pipeline.py: update fetch_recent_emails() to use SINCE today + fallback to ALL
- [ ] 3. matching_v2.py: add raw_body to project dict in fetch/query logic
- [ ] 4. matching_v2.py: add raw_body to engineer dict (from Notion field)
- [ ] 5. matching_v2.py: include raw_body in result.json output per item and per candidate
- [ ] 6. notify_line.py: add raw_body to get_page_info() project block
- [ ] 7. notify_line.py: add raw_body to get_page_info() engineer block
- [ ] 8. notify_line.py: add raw_body to empty_page_info() for both types
- [ ] 9. notify_line.py: main() fills project_info raw_body from result.json fallback
- [ ] 10. notify_line.py: main() fills engineer_info raw_body from candidate fallback
- [ ] 11. notify_line.py: build_project_message() appends project raw_body section
- [ ] 12. notify_line.py: build_project_message() appends per-engineer raw_body section
- [ ] 13. py_compile mail_pipeline/mail_pipeline.py -> no error
- [ ] 14. py_compile matching_v2/matching_v2.py -> no error
- [ ] 15. py_compile matching_v2/notify_line.py -> no error
- [ ] 16. python matching_v2/notify_line.py --dry-run -> exits 0 with raw_body shown
"""

for fname, content in [('CLAUDE.md', claude_md), ('SPEC.md', spec_md), ('TASKS.md', tasks_md)]:
    path = os.path.join(base, fname)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    size = os.path.getsize(path)
    print(f'written: {fname} ({size}B)')
