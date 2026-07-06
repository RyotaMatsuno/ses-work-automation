# GPT-5.4 Wall-Hit: Precision Round 3

## Priority: P0->P1->P2
P0: allowlist-first validator + post-extraction normalization + dictionary gating
P1: dictionary merge (conf>=0.95) + 125 review queue + inline nicesk parser
P2: price 132 fix + ERROR 1509 retry

## Key design decisions
- Allowlist overrides blacklist (validation order: alias hit->normalize->blacklist->review)
- Backfill must be conservative: dictionary-gated output only
- Do NOT backfill 7000+ old records. Active + recent 90 days only
- Post-extraction: strip suffixes (の経験/知識/開発経験/構築経験 etc)
- 尚可: inline pattern first, LLM fallback only if hint words present
