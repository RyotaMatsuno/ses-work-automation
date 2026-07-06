import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

prompt = """You are a devil's advocate technical advisor for a Japanese SES (System Engineer Staffing) business.
The team claims they've hit an accuracy ceiling after 4 rounds of improvement. Your job is to critically analyze their current metrics, identify ALL remaining improvement opportunities, and estimate the effort/impact of each.

## CURRENT STATE (案件DB 募集中 436 active projects)

### Notion案件DB Field Quality:
- 必要スキル(required skills) empty: 6.0% (26/436) — avg 5.3 skills per project
- 尚可スキル(preferred skills) empty: 62.2% (271/436) — avg 3.8 when present
- 単価(rate) empty: 15.4% (67/436) — avg 40万 (suspiciously low)
- 単価 distribution: <30万: 159, 30-50万: 33, 50-70万: 66, 70-90万: 89, >90万: 22
- 勤務地(location) empty: 29.1% (127/436)
- リモート(remote) empty: 100% (0/436) — NOT extracted at all
- 仕入単価(cost rate) empty: 100% — NOT extracted
- 案件詳細(detail text) empty: 0% (all have raw text)

### Matching Engine (matching_v3):
- Total processed: 3,125 cases
- ERROR: 1,509 (48.3%)
- matched: 1,178, ng: 432
- MATCH rate: 59.6% (of non-error cases)
- Avg matches per case (where >0): 128.5 ← WAY too high
- 0 matches: 651 (40.4%), 50+ matches: 327 (20.3%)

### Skill Dictionary:
- 530 canonical skills, 679 aliases, 857 total unique strings
- Multi_select format in Notion

### Classification:
- project: 2,239, skip: 3,769, other: 1,905, engineer: 817
- Classification accuracy: 96.4%

### What R1-R4 fixed:
- Required skills empty: 31% → 6%
- High quality (skills+rate): 21% → 81%
- Match avg: 114 → 4.3 (per引き継ぎ; current DB shows 128.5 overall which includes old data)
- Rate anomaly >200万: eliminated
- Dictionary: 12/278 → 530/679

## CRITICAL QUESTIONS:
1. Is 6% skill emptiness truly the floor? The raw detail text is 100% present — can LLM extract more?
2. 単価<30万 = 159 cases (36.4% of cases with rate data). In SES, rates below 35万 are extremely rare. Is this extraction error?
3. 尚可スキル 62% empty — is this really "no data in source email" or extraction failure?
4. リモート 100% empty — this data EXISTS in most SES project emails. Why zero extraction?
5. 勤務地 29% empty — location_extractor was built but not integrated. What's the expected improvement?
6. 1,509 ERROR records (48%) — these are from 6/5 legacy. Should they be retried or purged?
7. Avg 128.5 matches — matching is clearly too permissive. What scoring/filtering changes would bring this to 5-15 range?
8. 最高品質(all 4 fields) = 31.9% vs 高品質(2 fields) = 81.4% — can we close this gap?

## REQUESTED OUTPUT FORMAT:
For each improvement opportunity, provide:
- AREA: What's being improved
- CURRENT → TARGET: Specific numbers
- APPROACH: Technical method (1-2 sentences)
- EFFORT: Hours of Cursor work
- IMPACT: On matching quality (High/Medium/Low)
- RISK: What could go wrong
- PRIORITY: 1 (do now) / 2 (do next week) / 3 (backlog)

Also answer: Is the team correct that "code improvements can't move the needle much"? Or are they wrong?

Respond in English. Be ruthlessly specific with numbers."""

resp = requests.post(
    "https://api.openai.com/v1/responses",
    headers={
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "gpt-5.4",
        "input": [
            {"role": "system", "content": "You are a devil's advocate technical advisor. Be ruthlessly critical and specific."},
            {"role": "user", "content": prompt}
        ],
        "reasoning": {"effort": "low"},
        "max_output_tokens": 12000
    },
    timeout=120
)

if resp.status_code == 200:
    data = resp.json()
    # Extract text from output
    output = data.get("output", [])
    for item in output:
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    print(content["text"])
        elif item.get("type") == "text":
            print(item.get("text", ""))
else:
    print(f"ERROR: {resp.status_code}")
    print(resp.text[:2000])
