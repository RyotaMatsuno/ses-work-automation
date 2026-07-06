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


## 追加仕様（GPT-5.4壁打ち 2026-06-29反映）

### 修正1 補足: 粗利判定3値化

```python
# 変更後（3値化）
eng_actual = _actual_price(engineer.get("単価（万円）"))
case_max = _actual_price(case_json.get("price_max"))

if case_max is None or case_max == 0:
    reasons.append("案件単価不明")
    # → REVIEW（NGにしない）

elif eng_actual is not None and eng_actual > 0:
    # 実単価あり → 粗利判定有効
    gross = case_max - eng_actual
    if gross < 5.0:
        return "NG", [f"粗利不足: {gross:.1f}万 < 5万（案件{case_max}万 - 人員{eng_actual}万）"]

else:
    # 推定単価のみ or 単価欠損
    eng_estimated = _estimate_engineer_price(engineer)
    if eng_estimated is None or eng_estimated == 0:
        reasons.append("人員単価算出不能（REVIEW）")
    else:
        gross_est = case_max - eng_estimated
        if gross_est < 5.0:
            reasons.append(f"粗利不足見込み（推定）: {gross_est:.1f}万 < 5万（推定{eng_estimated}万）（REVIEW）")
        # → 推定単価のみではNGにしない。REVIEWとして人間確認。
```

**ルール**: 推定単価のみで自動NGしない。REVIEW扱いにして人間確認を入れる。

### 修正2 補足: 未知スキルの必須/尚可分け

```python
# 必須スキルに未知語 → REVIEW
if unknown_required:
    reasons.append(f"未知必須スキル（要確認）: {unknown_required}")

# 尚可スキルのみ未知語 → INFO（REVIEWトリガーにしない）
# → REVIEW爆増を防ぐ
```

### 修正3 補足: 並行スコア欠損時

```python
p_score = _calc_parallel_score(engineer)
if p_score is None:
    reasons.append("並行スコア算出不能")
    # → REVIEW（NGにしない）
elif p_score >= 5.0:
    return "NG", [f"並行スコア過多: {p_score:.1f}（上限5.0）"]
```

### 修正4 補足: filter例外時の挙動

```python
# fail-open方式（例外時は全件通す + WARNING log）
try:
    filter_with_flag = base_filter + [{"property": "提案対象フラグ", "checkbox": {"equals": True}}]
    pages = self._query_database(ENGINEER_DB_ID, {"filter": {"and": filter_with_flag}})
except Exception as exc:
    logger.warning("提案対象フラグfilter失敗、fallback to base filter: %s", exc)
    pages = self._query_database(ENGINEER_DB_ID, {"filter": {"and": base_filter}})
```

### Judge判定表（完全版）

| 条件 | 判定 | 根拠 |
|---|---|---|
| 実単価あり + 粗利 >= 5万 | PASS | 粗利確保 |
| 実単価あり + 粗利 < 5万 | NG | 粗利不足 |
| 推定単価のみ + 粗利見込み < 5万 | REVIEW | 推定のみでNG禁止 |
| 単価算出不能（実/推定とも不可） | REVIEW | データ不足 |
| 案件単価不明 | REVIEW | データ不足 |
| 必須スキルに未知語あり | REVIEW | 正規化辞書外 |
| 尚可スキルのみ未知語 | INFO（非REVIEW） | 爆増防止 |
| 並行スコア >= 5.0 | NG | 稼働逼迫 |
| 並行スコア欠損 | REVIEW | データ不足 |
| 提案対象フラグfilter失敗 | fail-open + WARNING | API障害対応 |

### 判定ログ必須フィールド

judge結果に以下を記録:
- `engineer_unit_price_source`: "actual" | "estimated" | "missing"
- `gross_profit_calc_status`: "ok" | "estimated" | "missing_input"
- `gross_profit_value`: float | null
- `judge_version`: "v5.1"（Phase 5適用後のバージョン）
