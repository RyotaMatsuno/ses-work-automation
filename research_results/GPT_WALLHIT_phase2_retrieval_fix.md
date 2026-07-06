# GPT-5.4壁打ち Round 2: 171→0修正方針
日時: 2026-06-26

## 合意事項
1. AND交差 → 閾値ベースに変更
2. 閾値: max(1, ceil(0.5 * len(required_strong)))
3. フィルター段階では重み付けなし（judge_with_metaが既に担当）
4. 候補爆発防止: Counter + top-N cap (50-100件)
5. OOV/低信頼fuzzyは分母から除外

## 承認コード

```python
from collections import Counter
import math

counter = Counter()
for skill in required:
    for eng_id in skill_index.get(skill, []):
        counter[eng_id] += 1

min_match = max(1, math.ceil(0.5 * len(required)))
candidate_ids = {eng_id for eng_id, cnt in counter.items() if cnt >= min_match}

# Optional: top-N cap before judge
scored = sorted(counter.items(), key=lambda x: -x[1])
candidate_ids = {eid for eid, _ in scored[:100] if counter[eid] >= min_match}
```
