# CEO Checkpoint 報告 — 精度改善 R5（CP1 + CP2）

**日時**: 2026-06-25  
**対象**: Task 04（merge_policy + backfill_engine + shadow mode + pilot 20件）  
**報告先**: 松野CEO

---

## エグゼクティブサマリー

R5の抽出基盤（rate / remote / location）を **安全にNotionへ反映する仕組み** を実装し、20件パイロットで本番検証を完了しました。

| 判定項目 | 結果 |
|---------|------|
| 既存スキル抽出の回帰 | **なし**（golden 60件 PASS） |
| 非空欄の意図しない上書き | **0件** |
| pilot書き込みエラー | **0件** |
| rollback動作 | **確認済み**（1件） |
| Phase C（段階backfill）への進行 | **GO推奨** |

---

## CP1: Backfill安全性（Task 04 完了内容）

### 実装済みコンポーネント

1. **`scripts/merge_policy.py`** — 空欄のみ埋める / confidence比較 / スキル非上書き
2. **`scripts/backfill_engine.py`** — dry-run → batch-id → PATCH → ログ
3. **`scripts/rollback_backfill.py`** — `backfill_logs/{batch_id}.json` から逆操作
4. **`mail_pipeline.py` shadow mode** — 新規メール取込時に v2 フィールドのみ付与

### Pilot結果（batch: `pilot_001`）

| 指標 | 値 |
|------|-----|
| 処理件数 | 20 |
| 変更件数 | 20 |
| エラー | 0 |
| needs_review超過（>5%） | なし（0%） |
| 非空上書き | **0** |

**rate_type 分布（20件）**

| タイプ | 件数 |
|--------|------|
| fixed_upper_only | 10 |
| not_present | 4 |
| fixed_range | 2 |
| skill_dependent_no_number | 2 |
| unknown | 2 |

**remote_type 分布（20件）**

| タイプ | 件数 |
|--------|------|
| onsite | 11 |
| hybrid | 6 |
| unknown | 2 |
| full_remote | 1 |

**特記事項**
- 単価0万 → null化: **2件**（抽出不能の0万を正しく空扱いに）
- rollback検証: 「NetView経験者募集」1件をロールバック成功（残り19件はv2適用済み）

### ベースライン（pre_r5、募集中469件）

| KPI | 値 |
|-----|-----|
| 単価空率（0万=空） | 49.5% |
| 勤務地空率 | 27.9% |
| remote_type空率 | 100%（導入前） |
| 必要スキル空率 | 5.5% |

---

## CP2: 品質ゲート（回帰・テスト）

| テスト | 結果 |
|--------|------|
| `golden_test/regression_test.py` | **PASS**（A30/B20/C10） |
| `extractors/test_extractors.py` | **29 PASS** |
| `scripts/tests/test_merge_policy.py` | **4 PASS** |
| `scripts/verify_notion_schema.py` | **PASS**（R5プロパティ6件） |

**ガードレール遵守**
- 必要スキル / 尚可スキル / 案件詳細は **一切未変更**
- LLMコスト: **$0**（regexのみ）
- dry-run → execute の順序を遵守

---

## 松野CEOへの確認依頼（手動5件）

Notion上で以下5件の目視確認をお願いします（pilot代表サンプル）:

1. **投資・資産運用会社のシステム開発** — rate: fixed_upper_only / remote: hybrid
2. **省庁向けNW構築 SD-WAN** — rate: fixed_range / remote: onsite
3. **システム改修案件（Java/Oracle）** — remote: full_remote
4. **サーバー・インフラ人材** — 単価0→null、rate: not_present
5. **ServiceNowの構築・運用/豊洲/常駐** — rate: unknown / remote: onsite

確認観点: rate_type・remote_typeが原文と矛盾していないか、既存スキル・単価（非0）が壊れていないか。

---

## 次ステップ推奨（Phase C: Task 05）

```powershell
# 100件バッチ（dry-run → execute）
python scripts/backfill_engine.py --dry-run --limit 100 --batch-id batch_100_001
python scripts/backfill_engine.py --execute --limit 100 --batch-id batch_100_001
```

**停止条件（自動監視済み）**: needs_review >5% / エラー率 >2% / 非空上書き検出

---

## リスクと対策

| リスク | 対策状況 |
|--------|----------|
| 良データ上書き | merge_policy + pilotで0件確認 |
| 0万の誤解釈 | not_present時はnull化（2件で動作確認） |
| ロールバック不能 | batch-idログ + rollbackスクリプト検証済み |
| R1-R4品質劣化 | golden回帰PASS |

**結論**: Phase C（100件→全件 backfill）への進行を **承認推奨** します。
