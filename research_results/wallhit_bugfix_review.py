import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

prompt = """You are a devil's advocate code reviewer for a Japanese SES automation system.
We ran a 20-case pilot backfill with new rate/remote/location extractors and found 3 bugs + 1 minor issue in 19 production records. Before we fix and proceed to batch backfill (449 remaining cases), review our proposed fixes.

## Bug 1: Rate unit conversion — 55万 stored as 550,000
**Symptom**: Case "生命保険システム基盤案件" has rate = 550,000 in Notion.
**Source text**: "単価：55万"
**Root cause hypothesis**: The extractor correctly captured "55" from the regex, but somewhere in the write path it multiplied by 10,000 (treating 万 as a unit multiplier instead of storing the raw 万-unit number).

**Proposed fix**: 
- In rate_extractor.py, ensure output is always in 万 units (the raw captured number)
- Add validation: any extracted rate > 200 → reject as anomaly (flag needs_review)
- In backfill_engine.py, add assertion: rate_max_man <= 200 before Notion write

**Question**: Is this the right root cause? Or could it be a Notion number field type issue?

## Bug 2: "N万（スキル見合い）" pattern not matched
**Symptom**: Case with "70万（スキル見合い）" got rate_type=skill_dependent_no_number instead of skill_dependent_with_cap with rate_max=70.
**Root cause**: Current regex order is:
1. `スキル見合い.*?(MAX|上限|〜)\\s*(\\d{2,3})\\s*万` — looks for スキル見合い BEFORE the number
2. But source has number BEFORE スキル見合い: "70万（スキル見合い）"

**Proposed fix**:
- Add reverse pattern: `(\\d{2,3})\\s*万.*?スキル見合` → skill_dependent_with_cap
- Add pattern: `(\\d{2,3})\\s*万円?\\s*前後` → fixed_upper_only (use number as max)
- Add pattern: `(\\d{2,3})\\s*万円?\\s*程度` → fixed_upper_only (use number as max)
- Insert these BEFORE the "スキル見合い only" pattern in priority order

**Question**: Are there other word-order variants we're missing?

## Bug 3: "初日出社有" overrides full_remote classification
**Symptom**: Case with "初日出社有" was classified as full_remote.
**Root cause**: The remote regex matched "リモート" in the subject/body earlier in processing, classified as full_remote. Then "初日出社有" in the notes section was not checked.

**Proposed fix**:
- After initial classification, scan for override patterns:
  - `初日出社` / `初月出社` / `立ち上がり出社` → set initial_onsite=True
  - If initial_onsite=True AND remote_type=full_remote → downgrade to hybrid or remote_possible
- Run override check AFTER primary classification

**Question**: Should "初日出社" make it hybrid or remote_possible? What's the SES business semantics?

## Minor: "50万円前後" not captured
**Symptom**: "50万円前後" resulted in rate_type=unknown.
**Fix**: Already covered by Bug 2 fix (adding 前後/程度 patterns).

## General questions:
1. Are these 3 fixes sufficient, or do you see other latent bugs we should catch before batch backfill?
2. Should we re-run the full 20-case pilot after fixes, or just verify the 3 broken cases?
3. Any risk that these fixes could regress the 15 correct cases?
4. The unit conversion bug (Bug 1) — should we scan ALL existing Notion records for >200万 values as a safety sweep?

Be specific. If our fix approach is wrong, tell us exactly why."""

resp = requests.post(
    "https://api.openai.com/v1/responses",
    headers={
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "gpt-5.4",
        "input": [
            {"role": "system", "content": "You are a devil's advocate code reviewer. Be specific about failure modes. Short, actionable answers."},
            {"role": "user", "content": prompt}
        ],
        "reasoning": {"effort": "low"},
        "max_output_tokens": 6000
    },
    timeout=120
)

if resp.status_code == 200:
    data = resp.json()
    output = data.get("output", [])
    result_text = ""
    for item in output:
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    result_text += content["text"]
    print(result_text)
else:
    print(f"ERROR: {resp.status_code}")
    print(resp.text[:2000])
