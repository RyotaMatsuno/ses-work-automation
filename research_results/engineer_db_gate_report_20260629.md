# Engineer DB Quality — Gate Report (2026-06-29)

## Gates

| Gate | 条件 | 結果 |
|------|------|------|
| F1 | 10件 apply、一致率 ≥ 80% | **PASS** (100%) |
| F3 | 50件、unknown率 ≤ 15% | **PASS** (0%) |
| F4 | 全件 apply、残更新候補 0 | **PASS** |

## Before / After（208件）

| フィールド | Before | After | 目標 |
|-----------|--------|-------|------|
| スキル | 173/208 (83%) | 201/208 (97%) | 空欄≤10 ✅ |
| 単価 | 173/208 (83%) | 191/208 (92%) | 空欄≤10 — 原文なし17件残 |
| 最寄り駅 | 4/208 (2%) | 139/208 (67%) | 120+ ✅ |
| 経験年数 | 120/208 (58%) | 122/208 (59%) | 150+ — 原文なし86件残 |
| 稼働可能日 | 57/208 (27%) | 172/208 (83%) | 100+ ✅ |

## スナップショット

- Before: `research_results/engineer_db_before_snapshot_20260629.json`
- After: `research_results/engineer_db_after_snapshot_20260629.json`
- Gate JSON: `research_results/engineer_db_gate_report_20260629.json`

## E4 修正サマリ

- `station_extractor.py`: 「り駅」誤マッチ修正、駅サフィックスなし対応
- `merge_policy.py`: 経験年数 min conf 0.70、最寄り駅 min conf 0.65
- `update_runner.py`: `--apply` バグ修正

## pytest

`engineer_extractor/tests/` — **65 passed**
