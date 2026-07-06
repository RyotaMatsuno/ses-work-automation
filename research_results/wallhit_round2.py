import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

round1_summary = """## Round 1 conclusions (accepted):
- Phase 0: KPI cohort separation + 20-30 case mini benchmark FIRST
- Phase 1: Location integration → Remote extractor → Rate 0万 reparse → ERROR retry
- Phase 2: Matching hard filters → scoring
- Phase 3: Preferred skills → Required skills fallback → Full benchmark
- Preferred skills demoted from Phase 1 to Phase 3 (overvalued)
- ERROR retry moved AFTER extraction fixes (dependency fix)"""

prompt = f"""You are a devil's advocate advisor for an SES automation system. This is Round 2 of 3.

{round1_summary}

## NEW DATA: Pattern analysis results

### Rate 0万 breakdown (168 cases stored as 0):
- スキル見合い (with extractable number like MAX/〜): 36 cases (21.4%)
- 〜N万 pattern: 16 cases (9.5%)  
- MAX N万: 5 cases (3.0%)
- N万 (plain number): 3 cases (1.8%)
- Budget word but unclear: 6 cases (3.6%)
- **TRULY NO RATE DATA in source**: 118 cases (70.2%)

So: 60 recoverable by regex, 6 need LLM, 118 should be NULL not 0.

### Remote pattern analysis (ALL 469 active cases):
- フルリモート/完全リモート: 58 (12.4%)
- ハイブリッド/週N出社: 83 (17.7%)
- 常駐/オンサイト: 124 (26.4%)
- リモート/テレワーク(ambiguous): 65 (13.9%)
- No mention at all: 139 (29.6%)
- **TOTAL EXTRACTABLE: 330 (70.4%)**

### Current system architecture:
- mail_pipeline.py runs every 30min via Windows Task Scheduler
- Uses gpt-4.1-nano for classification/structuring
- Writes to Notion案件DB via REST API
- matching_v3 runs daily at 08:00 (rule-based, LLM only for email draft)
- CostGuard: $8/day, $140/month, currently at 11.7%

## QUESTIONS FOR ROUND 2 (Technical approach):

### Q1: Rate 0万 fix — two-step approach
I'm thinking:
- Step 1 (regex, no LLM): Fix 60 cases with clear patterns (〜N万, MAX N, N万)
- Step 2 (no LLM needed): Convert 118 truly-empty cases from 0 → NULL
- Step 3 (LLM): Only 6 cases
Is this correct? Or should I use LLM for all 168 for consistency?

### Q2: Remote extractor — regex vs LLM
Pattern analysis shows 70.4% extractable with simple regex.
Should this be:
a) Pure regex (6 categories: full_remote/hybrid/onsite/partial/unknown/none)
b) LLM-assisted (more nuanced but costs more)
c) Regex first, LLM fallback for ambiguous?

### Q3: Matching hard filters — what specific filters?
Current matching_v3 is rule-based (no LLM). Average 128.5 matches.
What hard filters should be implemented, in what order?
- Required skill overlap threshold?
- Rate band compatibility?
- Location/remote compatibility?
- Something else?

### Q4: Pipeline integration risk
location_extractor and remote_extractor both need to be wired into mail_pipeline.py.
Should they:
a) Run at structuring time (when email is first processed)
b) Run as a batch backfill (process existing 469 cases, then add to pipeline)
c) Both (backfill + forward pipeline)

### Q5: "スキル見合い" problem
36 of the 0万 cases have "スキル見合い" — meaning "rate depends on skill level."
Of those, some also have a MAX value (e.g., "スキル見合い（MAX65万）").
For cases where it's JUST "スキル見合い" with no number, what should we store?
- NULL (no rate known)?
- A flag like "skill_dependent"?
- A estimated range based on required skills + industry norms?

### Q6: Mini benchmark design
How should the 20-30 case benchmark be structured?
- Which fields to annotate?
- How to select representative cases?
- How to score extraction accuracy?

Be specific and actionable. Give me the exact technical approach, not general advice."""

resp = requests.post(
    "https://api.openai.com/v1/responses",
    headers={
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "gpt-5.4",
        "input": [
            {"role": "system", "content": "You are a devil's advocate technical advisor. Give specific, actionable technical recommendations. No hand-waving."},
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
    with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\research_results\wallhit_R2_technical.md", 'w', encoding='utf-8') as f:
        f.write(f"# Round 2: Technical Approach\n\n{result_text}")
else:
    print(f"ERROR: {resp.status_code}")
    print(resp.text[:2000])
