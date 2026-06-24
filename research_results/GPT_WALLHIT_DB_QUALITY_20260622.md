# GPT Wall-Hit: DB Quality + Matching Precision Improvement
Date: 2026-06-22

## Current State (post-cleanup)
- 募集中 583件 → person leak 19件除去 + price anomaly 23件null化
- No skills: 56% / No price: 48% / No location: 22%

## Root Cause
- Pipeline uses AI-first extraction (gpt-4.1-nano) → fails on structured Japanese email formats
- No regex pre-extraction for price/skills from subject
- No post-AI validation (caps, ranges, unit detection)
- No skill dictionary fallback

## GPT Recommended Architecture (AGREED)
### Price: Rule-first, AI-secondary
1. Subject regex → body regex → AI fallback
2. Range → lower bound / Cap >200万 → null / Annual detection / Daily detection
3. Context classification (単価/年収/日額)

### Skills: 3-layer extraction
1. Header regex (必要スキル/必須/尚可 sections)
2. Known-skill dictionary scan
3. AI cleanup only

## Target Metrics
- No skills: 56% → 25-35%
- No price: 48% → 15-25%
- Price anomalies: near-zero
