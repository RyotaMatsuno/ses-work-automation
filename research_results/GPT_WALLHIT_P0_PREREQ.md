# GPT Wall-Hit + Verification: P0/Prerequisite/CostGuard Check
Date: 2026-06-19
Model: gpt-5.4

## P0 Status (all 3 RESOLVED)
1. DB work queue: Task N done. CostGuard throttle was blocking - PHASE_THRESHOLD and DAILY_CALL_LIMIT_CLASSIFY raised
2. BTM/NBW regex: Task A done. ENGINEER_PATTERNS fixed, PROJECT_PATTERNS has BTM/NBW案件
3. CostGuard silent-zero: Task C done. get_today_cost_usd removed, CostGuard v2 SQLite unified

## CostGuard Config Changes Applied
- PHASE_THRESHOLD_LIGHT: $0.025 -> $0.10
- DAILY_CALL_LIMIT_CLASSIFY: (new) 500 (temporary for backlog drain)
- DAILY_CALL_LIMIT_EXTRACT: (new) 100
- DAILY_CALL_LIMIT_MATCHING: (new) 30

## Nightly_jobz Prerequisite Bug Status

### Bug 1: mail_rest.py crash
- File exists, 754 lines, has try/except + __main__ guard + encoding handling
- Last modified 2026-06-19 12:17 (same day as other Cursor tasks)
- STATUS: Likely already fixed by Cursor - needs manual run test to confirm

### Bug 2: skill_judge.py CostGuard bypass
- matching_v2/skill_judge.py: BYPASS EXISTS (client.messages.create direct, no CostGuard)
- matching_v3/skill_judge.py: HAS CostGuard reference but also direct client.messages.create
- STATUS: matching_v2 is legacy (v3 is active), but v3 still has direct API call - needs Cursor fix

### Bug 3: .env variable name mismatch
- 26 env vars read in code but NOT defined in .env
- Key mismatches: NOTION_TOKEN, IMAP_HOST, IMAP_PORT, LINE_BRIDGE_* vars, LLM_MODEL, etc.
- Many are likely set elsewhere (system env, Cloud Run env) or have fallback defaults
- STATUS: Needs audit - some may be benign (hardcoded defaults), some may cause silent failures

## CostGuard Unification Gaps
- cost_log.jsonl still referenced in 61 files (mostly debug/check scripts, cost_guard.py docstring)
- 32 files with direct API calls without CostGuard (mostly debug scripts, wall_hitting, tmp files)
- Active production files with bypass: wall_hitting.py, double_check/double_check.py, gate_checker checks
- STATUS: Production-critical bypass is limited. wall_hitting.py is intentional (GPT consult). 
  double_check.py may need CostGuard integration.

## Recommended Next Steps
1. CLASSIFY=500 should drain 1429 backlog in ~3 days. Monitor 18:00 run.
2. Create Cursor task for skill_judge.py v3 CostGuard integration
3. Audit 26 missing .env vars - categorize as benign/needs-fix
4. After backlog drained, lower CLASSIFY to 200 (steady state)
