# 【Cursor作業指示】Task BF: マッチングロジック精度改善（重み設計 + 除外条件明確化）

対象ディレクトリ: ses_work/matching_v3/
作業内容: スキルマッチの重み付け改善と除外条件の厳格化
参照ファイル: CLAUDE.md / matching_v3/matcher.py / matching_v3/skill_judge.py / matching_v3/skill_aliases.json
完了条件: 必須/尚可の重み分離・除外条件追加・同義語展開のテスト通過
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 背景（GPT-5.4壁打ち合意済み）
- 構造化精度（Task BC）の次に改善すべきはマッチングロジック
- 「当たりを増やす」だけでなく「ハズレ提案を減らす」ことがSESでは重要（GPT指摘）

## 変更内容

### 1. スキルマッチの重み分離（matcher.py）

現行: 必須/尚可を同じ重みでスコアリング
変更: 必須と尚可で傾斜をつける

```python
WEIGHT_MUST_HAVE = 10    # 必須スキル1個一致 = +10
WEIGHT_NICE_TO_HAVE = 3  # 尚可スキル1個一致 = +3
WEIGHT_MUST_MISS = -100  # 必須スキル1個不一致 = -100（実質除外）
WEIGHT_PRICE_MATCH = 5   # 単価帯一致 = +5
WEIGHT_LOCATION = 3      # 勤務地一致 = +3
WEIGHT_REMOTE = 2        # リモート可 = +2
```

### 2. 除外条件の明確化（matcher.py judge関数）
以下はスコアに関係なく強制除外:
- 必須スキルに1つでも×がある
- 単価乖離5万超
- 外国籍人材（案件が外国籍不可の場合）
- 粗利5万未満になる組み合わせ
- 粗利15万超（スキル/価格ミスマッチの可能性）

### 3. 同義語展開の安全装置（skill_judge.py）
- Java ≠ JavaScript（明示的除外ルール）
- C ≠ C++ ≠ C#（明示的除外ルール）
- PM ≠ PMO（別スキル扱い）

同義語展開の除外リスト:
```python
NEVER_MERGE = [
    {"Java", "JavaScript"},
    {"C", "C++", "C#", "Objective-C"},
    {"PM", "PMO"},
    {"AWS", "Azure", "GCP"},
    {"React", "React Native"},
]
```

### 4. マッチスコアの透明化
- 各候補にスコア内訳を付与（デバッグ・品質管理用）
```json
{
  "name": "田中太郎",
  "total_score": 36,
  "breakdown": {
    "must_have": {"Java": 10, "Spring": 10},
    "nice_to_have": {"AWS": 3, "Docker": 3},
    "price": 5,
    "location": 3,
    "remote": 2
  }
}
```

## テスト
1. 必須スキル不一致で除外されるか
2. 重み計算が正しいか（必須>尚可）
3. 同義語展開でJava/JavaScriptが混同されないか
4. 粗利フィルター（5万下限・15万上限）が機能するか
5. 既存テスト全PASS
