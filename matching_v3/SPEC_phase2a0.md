# Phase 2A0: Retrieval Collapse Fix — SPEC.md
Version: 1.0
Date: 2026-06-26

## 背景
matching_v3のfilter_engineers_by_required_skillsがAND集合演算（交差）を使用しており、
必須スキル全一致を要求するため、ほぼ全案件で候補者が0名になっている。
- 現状: avg_matches = 0.2/案件
- 目標: avg_matches >= 3.0/案件（候補生成段階）

## 根本原因
matcher.py 497行目:
```python
candidate_ids = skill_ids if candidate_ids is None else candidate_ids & skill_ids
```
→ 全必須スキルのAND（積集合）。5スキル中1つでもエンジニアDBに存在しなければ0名。

## 修正方針（GPT-5.4合意済み）
AND交差を**閾値ベースのカウンティング方式**に変更。

### 新ロジック
```python
from collections import Counter
import math

def filter_engineers_by_required_skills(engineers, normalizer, skill_index, required_skills):
    if not required_skills:
        return engineers
    
    # 1. Resolve required skills to canonical forms
    resolved = []
    for skill in required_skills:
        canonical = normalizer.resolve_canonical(skill)
        if canonical:
            resolved.append(canonical)
    
    if not resolved:
        return []
    
    # 2. Count matches per engineer using index
    counter = Counter()
    for skill in resolved:
        for eng_id in skill_index.get(skill, set()):
            counter[eng_id] += 1
    
    # 3. Threshold: at least 50% of resolved skills (minimum 1)
    min_match = max(1, math.ceil(0.5 * len(resolved)))
    
    # 4. Filter and cap at top 100
    passing = [(eng_id, cnt) for eng_id, cnt in counter.items() if cnt >= min_match]
    passing.sort(key=lambda x: -x[1])
    candidate_ids = {eng_id for eng_id, _ in passing[:100]}
    
    return [eng for eng in engineers if eng.get("id") in candidate_ids]
```

## 変更対象ファイル
- matching_v3/matcher.py: filter_engineers_by_required_skills関数の書き換え
- matching_v3/tests/: テスト追加

## テスト要件
1. 既存テスト全PASS（回帰なし）
2. 新テスト:
   - 5スキル中3マッチ → 候補に含まれる
   - 5スキル中1マッチ → 候補に含まれない（閾値50%=3未満）
   - 2スキル中1マッチ → 候補に含まれる（min=max(1,1)=1）
   - 0スキル解決 → 空リスト返却
   - 100名超候補 → top100にキャップ
3. 実データ検証:
   - 直近20案件で再マッチング実行
   - avg_matchesが0.2→3.0以上になることを確認

## 制約
- judge_with_metaは変更しない（既存のスコアリングロジックをそのまま活用）
- apply_hard_filtersは変更しない
- 閾値50%は定数化してconfig.pyに移動
- CostGuard: LLM呼び出しなし（ルールベースのみ）

## リスク
- 候補爆発: top-100キャップで防止
- 精度低下: judge_with_metaが既にmiss_skills/unknown_skills/soft_hitsを分析するため、
  候補が増えてもスコアリングで適切にランク付けされる
