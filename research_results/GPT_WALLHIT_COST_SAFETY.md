# GPT Wall-Hit: Cost Safety + Nightly_jobz Go/No-Go
Date: 2026-06-19
Model: gpt-5.4

## Cost Safety: SAFE
- Daily projected: ~$1.15/day during drain (7x headroom vs $8 cap)
- Monthly: ~$8.85 after drain ($140 cap, 6.3%)
- Backlog worst case: ~$1.84 total

## Config Changes Applied
- PHASE_THRESHOLD_LIGHT: $1.00 (from $0.025, was blocking at $0.54 daily)
- PHASE_THRESHOLD_MEDIUM: $2.00
- PHASE_THRESHOLD_HEAVY: $1.00 (from $0.15)
- DAILY_CALL_LIMIT_CLASSIFY: 500
- DAILY_CALL_LIMIT_EXTRACT: 500 (GPT caught: 100 would take 12 days instead of 3)
- DAILY_CALL_LIMIT_MATCHING: 30

## GPT Verdict: GO for nightly_jobz
Conditions:
1. CostGuard v3 active in nightly path (confirmed)
2. Missing env vars don't affect model/retries/caps (low risk)
3. mail_rest failure non-fatal (confirmed)

## Key GPT Warnings (addressed)
- Extract call limit was bottleneck (raised 100->500)
- PHASE_THRESHOLD_HEAVY was too low (raised $0.15->$1.00)
- Retry amplification risk exists but CostGuard catches it
- Backlog drain: 3-5 days realistic with current limits

## Post-drain steady state (to set after backlog cleared)
- DAILY_CALL_LIMIT_CLASSIFY: 200 (normal daily inflow ~100-200)
- DAILY_CALL_LIMIT_EXTRACT: 200
- PHASE_THRESHOLD_LIGHT: $0.50
