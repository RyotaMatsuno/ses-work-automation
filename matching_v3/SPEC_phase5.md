# Phase5 SPEC: マッチング判定ロジック品質修正

## 修正1: 単価バンドを粗利5万床に修正（judge関数）

```python
# 変更前
eng_price = float(engineer.get("単価（万円）") or 0)
case_max = float(case_json.get("price_max") or 0)
if case_max > 0 and eng_price > case_max + 15:
    return "NG", [f"単価超過: {eng_price}万 > 案件上限{case_max}+15万"]

# 変更後
eng_price = float(engineer.get("単価（万円）") or 0)
case_max = float(case_json.get("price_max") or 0)
if case_max > 0 and eng_price > 0:
    gross = case_max - eng_price
    if gross < 5.0:
        return "NG", [f"粗利不足: {gross:.1f}万 < 5万（案件{case_max}万 - 人員{eng_price}万）"]
elif case_max > 0 and eng_price == 0:
    reasons.append("人員単価不明")
```

## 修正2: 未知必須スキルをREVIEW要因に（judge関数）

```python
# 変更前（normalize失敗を黙殺）
for skill in required_raw:
    normalized = normalizer.normalize(skill)
    if normalized and normalized not in eng_skills:
        missing.append(normalized)
if missing:
    return "NG", [f"必須スキル不足: {missing}"]

# 変更後
unknown_required = []
for skill in required_raw:
    normalized = normalizer.normalize(skill)
    if normalized is None:
        unknown_required.append(skill)  # 未知スキルはREVIEW
    elif normalized not in eng_skills:
        missing.append(normalized)

if missing:
    return "NG", [f"必須スキル不足: {missing}"]
if unknown_required:
    reasons.append(f"未知必須スキル（要確認）: {unknown_required}")
```

## 修正3: 並行スコア超過をNGに（judge関数）

```python
# 変更前
p_score = _calc_parallel_score(engineer)
if p_score >= 5.0:
    reasons.append(f"並行スコア過多: {p_score:.1f}")

# 変更後
p_score = _calc_parallel_score(engineer)
if p_score >= 5.0:
    return "NG", [f"並行スコア過多: {p_score:.1f}（上限5.0）"]
```

## 修正4: get_active_engineers に提案対象フラグフィルタを追加

`notion_client.py` の `get_active_engineers()` のfilterに追加:
```python
# 既存のfilter["and"]リストに追加
{
    "property": "提案対象フラグ",
    "checkbox": {"equals": True}
},
```
※ただし、Notion DBに「提案対象フラグ」プロパティが存在しない場合は、
  このfilterを追加するとAPI 400エラーになる可能性がある。
  そのため、try-exceptで囲んでフィルタ有りを試み、失敗したら既存フィルタで再実行する実装にすること。

## 完了確認
- judge()で gross < 5.0 のNGチェックが存在する
- judge()で unknown_required の REVIEW 処理が存在する
- judge()で p_score >= 5.0 が NG を返す
- notion_client.py のget_active_engineersに提案対象フラグfilterが含まれる
