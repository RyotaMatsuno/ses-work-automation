import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import os
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

prompt = """SES matching engine quality review. I just examined ALL 45 matched cases from today's run. Three critical problems make this NOT production-ready.

## Problem 1: "語彙外スキル" causes mass false matches (CRITICAL)
When required skills are NOT in the skill dictionary (530 canonical), the skill filter can't work. Result: 36-52 engineers matched per case via REVIEW verdict.

Examples of out-of-vocabulary skills causing mass matches:
- UnrealEngine, Blueprint → 47 matches
- Informatica CDI → 40 matches
- IntraMart, IM-FormaDesigner → 39 matches
- WinActor → 36 matches
- Databricks, Azure運用保守 → 51 matches
- "課題" (the word "issue" was extracted as a required skill!) → 52 matches

The current behavior: if ALL required skills are out-of-vocab, the skill filter passes everyone → mass matches.

## Problem 2: "13件固定パターン" — Same 13 engineers for every low-quality case
Cases with extraction confidence 0.25 (NEEDS_REVIEW) always match the same 13 engineers: Y., KK, R., C., K., K., M., H., Y., P., TA, S., U.

This happens for:
- 沖縄ホテル情シス (Okinawa - should NOT match Tokyo engineers)
- 営業マーケティングSNS (not IT)
- Dynamics365 (out-of-vocab)
- C++ (out-of-vocab but should be in dictionary!)
- グローバル商品推進部 (not IT)

These 13 are likely engineers with very broad skills or empty skill lists that pass every filter.

## Problem 3: Skill extraction quality issues
Invalid "skills" being extracted as required:
- 「課題」(issue/task) — common Japanese word, NOT a skill
- 「能動的行動」(proactive behavior) — personality trait
- 「勤怠安定性」(attendance stability) — behavioral
- 「java案件】java」— malformed with bracket characters
- 「運転免許」(driver's license) — non-IT requirement

These pass validate_skill but shouldn't be treated as matchable technical skills.

## Current stats:
- 157 cases processed, 45 with matches (29%)
- avg matches per case (where >0): 10.6
- But removing the mass-match cases: would be ~3-5
- MATCH verdicts: ~15% of matched pairs (good matches)
- REVIEW verdicts: ~85% (mostly false positives from vocab gaps)

## Questions:
1. For out-of-vocab skills: should the system (a) reject the match entirely, (b) cap at N matches, or (c) try fuzzy matching?
2. For the "13 fixed engineers" pattern: what causes this and how to fix?
3. Should C++, Dynamics365, WinActor, etc. be added to skill dictionary?
4. For non-technical "skills" (課題, 能動的行動): should validate_skill block these, or should matching ignore them?
5. What's the minimum viable fix to make this production-usable?

Be specific and prioritized. I need the top 3 fixes that will have the biggest impact."""

resp = requests.post(
    "https://api.openai.com/v1/responses",
    headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
    json={
        "model": "gpt-5.4",
        "input": [
            {"role": "system", "content": "SES matching engine advisor. Be specific and prioritized. Top 3 fixes only."},
            {"role": "user", "content": prompt}
        ],
        "reasoning": {"effort": "low"},
        "max_output_tokens": 5000
    },
    timeout=120
)

if resp.status_code == 200:
    data = resp.json()
    for item in data.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    print(c["text"])
    # Save
    with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\research_results\GPT_WALLHIT_matching_quality.md", 'w', encoding='utf-8') as f:
        f.write(c["text"])
else:
    print(f"ERROR: {resp.status_code}")
    print(resp.text[:500])
