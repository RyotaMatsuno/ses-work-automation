import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

prompt = """SES automation system status review. All R5 phases completed by Cursor. Need your assessment of results and what (if anything) remains.

## R5 Results: BEFORE → AFTER

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| 必要スキル空 | 6.0% | 5.2% | 1-2% |
| 単価空(修正版) | 49.5% | 38.6% | <15% |
| 勤務地空 | 29.1% | 25.2% | 5-10% |
| リモート空 | 100.0% | **0.0%** | 70-85% achieved |
| 高品質(skill+rate) | 46.1% | **59.6%** | 70-80% |
| 最高品質(4 fields) | 24.9% | **55.1%** | 60-70% |
| v2 coverage | 4.3% | **100.0%** | — |

## Rate type distribution (n=497):
- not_present: 42.1% (source email has no rate info)
- fixed_upper_only: 29.4%
- fixed_range: 15.7%
- unknown: 5.6%
- skill_dependent_no_number: 5.2%
- skill_dependent_with_cap: 2.0%

## Remote type distribution:
- unknown: 29.4%
- onsite: 28.4%
- hybrid: 19.1%
- remote_possible: 12.7%
- full_remote: 10.5%

## What was completed:
1. Extractors (rate/remote/location) implemented as pure functions
2. 369-case batch backfill: 100% success, 0 errors
3. Matching hard filters implemented: rate + remote/location + skill_threshold + start_timing
4. Bug fixes: unit conversion, pattern order, 初日出社 semantics
5. Safety scan: 169 anomalies identified
6. Regression tests: all PASS

## What's still in pending_tasks/:
- 05_batch_backfill__try2.md (may be stale)
- 06_matching_hardfilter__try1.md (already implemented by Cursor)

## Current concerns:
1. 単価空 38.6% — not_present=42%. Is this the true ceiling (source has no rate)?
2. 勤務地空 25.2% — location_extractor was integrated but improvement was small
3. リモート unknown 29.4% — can regex extract more or is this the ceiling?
4. Matching hardfilter is implemented but we haven't measured new avg match count yet
5. 0万 still 20 cases remaining

## Questions:
1. For 単価 not_present (42%): is this truly "no data in source" or is the extractor still missing patterns?
2. Should we accept these numbers and move on to other business priorities?
3. What's the single most impactful remaining action (if any)?
4. Is it worth doing more rounds, or has R5 captured most of the value?

Be concise. Give a clear GO/STOP recommendation."""

resp = requests.post(
    "https://api.openai.com/v1/responses",
    headers={
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "gpt-5.4",
        "input": [
            {"role": "system", "content": "You are a pragmatic technical advisor. Be concise and decisive. No hand-waving."},
            {"role": "user", "content": prompt}
        ],
        "reasoning": {"effort": "low"},
        "max_output_tokens": 4000
    },
    timeout=120
)

if resp.status_code == 200:
    data = resp.json()
    output = data.get("output", [])
    for item in output:
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    print(content["text"])
else:
    print(f"ERROR: {resp.status_code}")
    print(resp.text[:1000])
