# GPT-5.4 Wall-Hit: Precision Improvement 2026-06-24
## Round 1: Problem Analysis
- Highest ROI: Controlled canonical skill pipeline with strict write validation
- Multi-select pollution is #1 precision killer (517 unique, 16% coverage, 431 garbage)
- 50% ERROR rate = historical backlog (all from 6/5), not ongoing
- Do NOT auto-convert annual salaries; flag and null instead
- Engineer station data: switch to coarse location (prefecture/remote) instead of station

## Round 2: Task Plan Review
- Blacklist-only is risky → allowlist + blacklist combined approach
- Do NOT globally delete Notion multi_select options → unlink from records first
- ERROR retry: small batches (50-100 first), not all 1509 at once
- Parallelize code changes, NOT mass write operations
- Investigate WHY 757 matches happen, not just cap at 20
- Add dry-run modes for all cleanup/trim operations
- Maintain 3-tier: canonical / alias / review queue
