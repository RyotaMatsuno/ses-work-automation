import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

prompt = """You are a devil's advocate advisor for an SES automation system. This is Round 3 of 3 (final).

## Round 1-2 summary (all accepted):
### Agreed execution plan:
- Phase 0 (Day 1-2): KPI cohort separation + 30-case mini benchmark
- Phase 1 (Week 1): Location integration → Remote extractor → Rate 0万 reparse → ERROR retry
- Phase 2 (Week 2): Matching hard filters (status → rate → remote/location → skill → experience → timing)
- Phase 3 (Later): Preferred skills, required skills fallback, full benchmark

### Agreed technical approach:
- Rate: 3-pass (regex → NULL for truly-empty → LLM fallback for 6 cases)
- Remote: regex-first (70.4% extractable), LLM for <15% ambiguous
- Extractors as pure functions in extractors/ directory
- Backfill existing 469 + forward pipeline integration
- スキル見合い → rate_type enum (skill_dependent_no_number / skill_dependent_with_cap)
- Notion schema additions: rate_type, remote_type, extraction_method, confidence

### System constraints:
- 2-person company, CEO (松野) has ~1-2 hours/day for review/testing
- All code implementation by Cursor (Claude-based IDE)
- Cursor tasks are markdown files in pending_tasks/. Each task = 2-4 hours of Cursor work.
- CostGuard: $8/day, $140/month (currently at $16.35/month = 11.7%)
- Matching runs daily at 08:00, mail_pipeline every 30min
- R1-R4 just completed: skill extraction 31%→6% empty, dictionary 12→530 canonical

## ROUND 3 FOCUS: Risks, failure modes, final plan

### Q1: Regression risk
R1-R4 fixed critical extraction issues. Adding new extractors and modifying pipeline could regress these.
- How do I protect R1-R4 gains while implementing new changes?
- Should I version the pipeline and run old+new in parallel?
- What's the minimum test to ensure no regression?

### Q2: Notion schema change risk
Adding rate_type, remote_type, etc. to the案件DB requires schema changes.
- Can Notion multi_select/select fields be added without breaking existing pages?
- What's the safest way to add these fields?
- Should I use existing fields differently or add new ones?

### Q3: Backfill safety
Running backfill on 469 active cases could corrupt good data.
- What safeguards are needed?
- How to make it reversible?
- Should I backfill in batches or all at once?

### Q4: Cursor task granularity
Each task is a markdown file that Cursor processes. Too big = failure rate increases. Too small = management overhead.
- What's the optimal number of Cursor tasks for this plan?
- How should they be sequenced?
- What should each task's acceptance criteria be?

### Q5: CEO review bottleneck
松野 has limited review time. The plan has 3 weeks of work.
- Which items REQUIRE CEO review before proceeding?
- Which can be fully autonomous (no CEO review)?
- What's the minimum CEO touchpoints for the full plan?

### Q6: CostGuard budget
ERROR retry of 1,509 records + LLM fallback for rate/remote.
- Estimate the total LLM cost for the full plan
- Will it fit within CostGuard limits?
- How to phase it to stay within $8/day?

### Q7: What am I still wrong about?
After 2 rounds, what am I likely still getting wrong or underestimating?
What's the #1 thing that will go wrong during execution?

Give me the final, concrete, executable plan with exact task list, ordering, dependencies, and CEO checkpoints. This is the plan we'll execute starting tomorrow."""

resp = requests.post(
    "https://api.openai.com/v1/responses",
    headers={
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "gpt-5.4",
        "input": [
            {"role": "system", "content": "You are a devil's advocate advisor giving final execution guidance. Be concrete, specific, and warn about what will go wrong. This is the last round - make it count."},
            {"role": "user", "content": prompt}
        ],
        "reasoning": {"effort": "low"},
        "max_output_tokens": 12000
    },
    timeout=180
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
    with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\research_results\wallhit_R3_risks_final.md", 'w', encoding='utf-8') as f:
        f.write(f"# Round 3: Risks & Final Plan\n\n{result_text}")
else:
    print(f"ERROR: {resp.status_code}")
    print(resp.text[:2000])
