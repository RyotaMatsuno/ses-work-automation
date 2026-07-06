import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import os
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

prompt = """I need to define requirements for a "commercially sellable" SES (System Engineer Staffing) matching engine. CEO wants it to be good enough to sell to other SES companies as a product.

## Current system state

### Project DB (案件DB): R5 completed, decent quality
- 497 active projects
- Required skills populated: 94.8%
- Rate populated (real): 61.4%
- Location populated: 74.8%
- Remote type: 100% populated
- Extraction pipeline: mail → LLM classify → rule-based extract → Notion

### Engineer DB: CRITICAL QUALITY PROBLEMS
- 208 engineers total (mix of active/inactive/candidates)
- **Desired rate: 0% populated** (100% empty!) → rate filter is non-functional
- Skills populated: 83.2% (35 engineers have ZERO skills)
- Of those with skills: avg 4.5 skills per engineer
- Many engineers have detailed info in raw text memos but skills NOT extracted
- Status field (稼働状況): has data but unclear if matching uses it
- No location/commute data for engineers
- No experience years for most

### Matching engine (matching_v3): R5 fixes applied
- Rule-based matching (no LLM)
- Skill dictionary: 530 canonical + 679 aliases
- Hard filters: rate + remote/location + skill threshold + start timing
- OOV fail-closed + low-quality gate
- Current result: avg 0.18 matches/case (most cases: 0 matches)
- 208 engineers × 497 projects = ~103,000 possible pairs

### Business context
- 2-person SES company (CEO + partner)
- 15 active workers currently
- Handles BP (business partner) engineer placements
- Revenue model: margin on monthly rates (5-8万/person/month)
- Currently: CEO manually reviews matches

## What "commercially sellable" means to the CEO
- Other SES companies could use this to match their engineers to projects
- Must reduce manual work significantly
- Must not miss good matches (high recall)
- Must not suggest bad matches (high precision)
- Must be explainable ("why was this match suggested?")

## Questions for requirements definition

### 1. Data quality requirements
- What's the minimum engineer data quality for matching to work?
- Should engineer skill extraction from raw text be automated (like project extraction)?
- What fields are essential vs nice-to-have?

### 2. Matching quality metrics
- What precision/recall targets make sense for SES?
- How should we measure quality without ground truth?
- What's a good benchmark methodology?

### 3. Architecture gaps
- Current system is rule-based only. Should it stay rule-based or add LLM scoring?
- Should matching be real-time or batch?
- How should results be presented to users?

### 4. Missing capabilities for commercial product
- What features do competing SES matching tools have?
- What's the MVP feature set?
- What's the roadmap priority?

### 5. Evaluation methodology
- How do we prove this works before selling it?
- What metrics would an SES company buyer care about?
- How do we build a ground truth dataset?

Give me a structured requirements document outline. Be specific to SES industry, not generic ML/matching advice. Include concrete numbers where possible."""

resp = requests.post(
    "https://api.openai.com/v1/responses",
    headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
    json={
        "model": "gpt-5.4",
        "input": [
            {"role": "system", "content": "You are a product/engineering advisor for SES (System Engineer Staffing) businesses in Japan. Give specific, actionable requirements with concrete numbers. Focus on what makes SES matching different from general job matching."},
            {"role": "user", "content": prompt}
        ],
        "reasoning": {"effort": "low"},
        "max_output_tokens": 12000
    },
    timeout=180
)

if resp.status_code == 200:
    data = resp.json()
    result_text = ""
    for item in data.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    result_text += c["text"]
    print(result_text[:8000])
    # Save full result
    with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\research_results\GPT_WALLHIT_commercial_requirements.md", 'w', encoding='utf-8') as f:
        f.write("# GPT-5.4: Commercial SES Matching Requirements\n\n" + result_text)
    print("\n\n[SAVED to research_results/GPT_WALLHIT_commercial_requirements.md]")
else:
    print(f"ERROR: {resp.status_code}")
    print(resp.text[:1000])
