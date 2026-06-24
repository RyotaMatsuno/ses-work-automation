# SPEC_stale_fix.md — 未実装項目一覧

作成日: 2026-06-09  
根拠: STATUS_20260609.txt ① の現状確認結果

---

## 未実装 / 未完了項目

### 1. 未登録必須スキル → REVIEW ロジックの削除

| 項目 | 内容 |
|---|---|
| 状態 | ❌ 未完了 |
| 対象ファイル | `matcher.py` `judge()` |
| 現状 | L62-63 で `normalized is None` の必須スキルを `未登録必須スキル要確認` として reasons に追加し、最終的に REVIEW になる |
| 期待動作 | MATCHER_FIX.md 記載のとおり、正規化不能スキル（未知スキル）は REVIEW 理由にしない。正規化できたスキルのみ不足チェック対象とする |
| 参照 | `MATCHER_FIX.md`, `SPEC.md` §6.3 |

#### 修正方針

`judge()` 内の必須スキルループを以下に変更する:

```python
for skill in required_raw:
    normalized = normalizer.normalize(skill)
    if normalized and normalized not in eng_skills:
        missing.append(normalized)
    # normalized が None の場合（未知スキル）は何もしない
if missing:
    return "NG", [f"必須スキル不足: {missing}"]
```

削除対象（現行コード）:

```python
if normalized is None:
    reasons.append(f"未登録必須スキル要確認: {skill}")
```

#### 影響

- `logs/match_results.jsonl` に大量出力されている `未登録必須スキル要確認` による REVIEW が解消される見込み
- 既存 pytest 23 件は現状パス。修正後も `test_ng_required_skill_missing` 等が通ることを再確認すること

#### テスト追加（推奨）

- 未登録必須スキル（aliases 外）のみの案件 + エンジニアが他条件を満たす場合 → MATCH になること
- 登録済み必須スキル不足の場合 → 従来どおり NG になること

---

## 実装済み項目（参考）

以下は STATUS_20260609.txt で ✅ 確認済み。本 SPEC の対象外。

| 項目 | 実装箇所 |
|---|---|
| staleness 21日 | `matcher.py` `ENGINEER_STALENESS_DAYS = 21`, `notion_client.py` |
| 粗利5万未満NG | `matcher.py` `GROSS_THRESHOLDS`, `judge()` |
| 並行スコア5.0超NG | `matcher.py` `_calc_parallel_score()`, `judge()` |
| 提案対象フラグフィルタ | `notion_client.py` `get_active_engineers()` |
