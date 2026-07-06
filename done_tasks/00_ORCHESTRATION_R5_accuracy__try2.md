# 00_ORCHESTRATION — 精度改善R5（抽出品質+マッチング精度）
# 生成: 20260625_143203
# 総タスク数: 8
# 松野チェックポイント: 3回（CP1:Task5後, CP2:Task6後, CP3:Task8後）

## Phase順序（厳守）

### Phase A（並列OK: Task 1,2,3）✅ 2026-06-25 DONE
- 01_baseline_golden_set.md — ベースライン凍結+60件ゴールデンセット ✅
- 02_notion_schema.md — Notionスキーマ追加（rate_type/remote_type等） ✅
- 03_extractors.md — 純粋関数extractor実装（rate/remote/location） ✅

### Phase B（Phase A完了後）✅ 2026-06-25 DONE
- 04_merge_backfill_engine.md — マージポリシー+dry-run/rollback+shadow mode統合+20件pilot backfill ✅

### Phase C（Phase B + CEO CP1,CP2 通過後）⏸ 待機中（松野承認待ち）
- 05_batch_backfill.md — 段階backfill（100件→残り全件）

### Phase D（Phase C完了後）
- 06_matching_hardfilter.md — マッチングhard filter有効化

## ガードレール（全タスク共通）
1. 抽出ロジック変更とバックフィルを同じcommitに混ぜない
2. mass writeは必ず dry-run → diff log → batch-id → rollback path
3. マッチング変更はshadow mode + pilot通過後のみ
4. LLMはフォールバック限定（regex優先）
5. 空欄は埋める、非空欄は上書きしない（confidence比較でのみ上書き許可）
6. CostGuard制約: LLM抽出は1日100-150コール上限

## 依存関係図
T1 ──┐
T2 ──┼──→ T4 ──→ T5(CP1) ──→ T6(CP2) ──→ T7 ──→ T8(CP3)
T3 ──┘


## RETRY 1 REASON
target_file not found: 


## RETRY 2 REASON
exit=1 / stderr=
