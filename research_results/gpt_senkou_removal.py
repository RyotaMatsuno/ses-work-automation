import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import os
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

prompt = """SES automation system. CEO decided to abolish the "選考中" (under review) status from the project DB.
Currently there are only: 募集中 (active), 終了 (closed), 営業終了 (sales closed).
All 562 選考中 records have been changed to 終了.

Now I need to remove 選考中 from the codebase. Here are the files that reference it:

**Production code (must change):**
1. `matching_v3/notion_client.py:153` — SETS status to 選考中 when creating/updating
2. `line_webhook/webhook_server.py:1084,1091,1308,1411` — includes 選考中 in query filters for matching
3. `daily_report.py:29` — ACTIVE_STATUSES = ("募集中", "選考中")

**Utility scripts (may need change):**
4. `check_case_count.py` — counts 選考中 in status checks
5. `check_status.py` — iterates over 選考中

**Spec/design files (no runtime impact):**
6. `write_daily_report_spec.py`, `write_spec_linequery.py` — documentation only

**Archive (deprecated, no impact):**
7. `_archive_tmp/` files — already deprecated

**Today's cleanup scripts (can delete):**
8. `research_results/close_senkou*.py` — one-off scripts

## Questions:
1. For `notion_client.py:153` which SETS status to 選考中 — what should it do instead? Keep 募集中? Not change status at all?
2. For `webhook_server.py` filters that include 選考中 — just remove 選考中 from the OR filter, keeping 募集中 only?
3. For `daily_report.py` — change to ACTIVE_STATUSES = ("募集中",)?
4. Should we also remove 選考中 from the Notion DB's select options?
5. Any risk of breaking matching or webhook behavior?
6. Should this be one Cursor task or multiple?

Be concise and specific."""

resp = requests.post(
    "https://api.openai.com/v1/responses",
    headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
    json={
        "model": "gpt-5.4",
        "input": [
            {"role": "system", "content": "Concise technical advisor. Give specific, actionable answers."},
            {"role": "user", "content": prompt}
        ],
        "reasoning": {"effort": "low"},
        "max_output_tokens": 3000
    },
    timeout=60
)

if resp.status_code == 200:
    data = resp.json()
    for item in data.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    print(c["text"])
else:
    print(f"ERROR: {resp.status_code}")
    print(resp.text[:500])
