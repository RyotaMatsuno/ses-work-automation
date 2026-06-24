# 【Cursor作業指示】Task AL: Tier3抽象語ゲーティング＋soft_aliases昇格

対象: ses_work/matching_v3/
参照: CLAUDE.md / matcher.py / skill_aliases.json
完了条件: Tier3語のみMATCHが不可 + soft_aliasesがPARTIAL_MATCH判定可能

## 変更
1. skill_aliases.jsonにtierフィールド追加: 各canonicalに "tier": 1/2/3
   - Tier3: クラウド, ネットワーク, RDBMS, ETL, DWH, AI, セキュリティ, インフラ, DB
2. judge()改修:
   - hit_skillsをtier別に集計: tier1_hits, tier2_hits, tier3_hits
   - Tier3のみヒット → MATCH不可（Tier1/2が1件以上必要）
   - Tier3はスコア加点のみ
3. soft_aliases昇格:
   - requiredスキルがsoft_aliasでのみ満たされる場合 → "PARTIAL_MATCH"判定
   - PARTIAL_MATCHはMATCH/REVIEWの中間（提案可能だが確認推奨）
4. score_components追加: exact_count, alias_count, soft_alias_count, tier3_count

## テスト
- Tier3のみ一致 → REVIEW
- Tier1+Tier3一致 → MATCH
- soft_alias一致 → PARTIAL_MATCH
