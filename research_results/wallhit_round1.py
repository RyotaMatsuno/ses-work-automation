import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

prompt = """You are a devil's advocate advisor for an SES (System Engineer Staffing) automation system.
We just completed a deep analysis and identified 8 improvement areas. Now I need you to challenge my thinking on PRIORITY ORDER and DEPENDENCIES.

## Context
- 2-person SES company (CEO + partner), fully automated pipeline
- Cursor (Claude-based IDE) handles all code implementation
- Each "task" = ~1 Cursor instruction file, takes 2-4 hours
- CEO has limited time for review/testing
- CostGuard budget: $8/day, $140/month for LLM calls
- Current monthly LLM spend: ~$16.35 (11.7% of cap)

## The 8 improvement areas with current metrics

1. **Rate 0万 reparse** — 168 cases stored as 0万 when source has "〜70万", "MAX65万", "スキル見合い"
   - True rate empty: 49.5% (was reported as 15.4%)
   - True high quality: 46.1% (was reported as 81.4%)

2. **Remote extractor (new)** — 0% populated, data exists in source emails
   - Patterns: フルリモート, 週N出社, 常駐, リモート併用, テレワーク, 在宅

3. **Location extractor integration** — 29.1% empty, extractor already built but not wired
   - Just pipeline integration work

4. **ERROR 1,509 retry + KPI cohort separation** — 48.3% of matching records are ERROR
   - All from 6/5 legacy bug. Current pipeline produces 0 errors.

5. **Required skills LLM fallback (26 empty cases)** — 6% → 1-2%
   - Small absolute count but improves floor

6. **Preferred skills extraction enhancement** — 62% empty → 30-40%
   - Detect 歓迎/優遇/あると尚可 patterns

7. **Matching hard filters** — avg 128.5 matches → 5-15
   - Requires clean rate + location + remote data first

8. **100-case benchmark set** — No ground truth exists today

## My current thinking on order

**Phase A (extraction quality — week 1):**
- Rate 0万 reparse (biggest impact on "true quality" metric)
- Remote extractor (new feature, 0→70-85%)
- Location extractor integration (already built)
- Preferred skills enhancement

**Phase B (matching quality — week 2):**
- Matching hard filters (depends on Phase A data quality)
- Rate/location/remote-aware scoring

**Phase C (cleanup — whenever):**
- ERROR retry/purge + KPI cohort separation
- Benchmark set
- Required skills LLM fallback (only 26 cases)

## Questions for you
1. Is my Phase A→B→C ordering correct? Should anything move?
2. Should the benchmark set come FIRST (before Phase A) so we can measure improvement? Or is that perfectionism?
3. Within Phase A, what's the right sub-order? Rate first? Remote first?
4. The CostGuard budget is $8/day. Rate reparse needs LLM calls (re-extract from raw text). Can 168 cases fit within budget?
5. Am I making any dependency errors?
6. What's the single most important thing I should NOT skip?

Be specific and critical. If my ordering is wrong, tell me exactly why and what the correct order is."""

resp = requests.post(
    "https://api.openai.com/v1/responses",
    headers={
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "gpt-5.4",
        "input": [
            {"role": "system", "content": "You are a devil's advocate advisor. Be ruthlessly critical about priority ordering and dependencies. Do not be diplomatic."},
            {"role": "user", "content": prompt}
        ],
        "reasoning": {"effort": "low"},
        "max_output_tokens": 12000
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
    # Save for next round
    with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\research_results\wallhit_R1_priority.md", 'w', encoding='utf-8') as f:
        f.write(f"# Round 1: Priority & Dependencies\n\n{result_text}")
else:
    print(f"ERROR: {resp.status_code}")
    print(resp.text[:2000])
