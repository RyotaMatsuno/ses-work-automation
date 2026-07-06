# Phase 2A0: Retrieval Collapse Fix — TASKS.md

## チェックリスト

- [x] T1: matcher.py の filter_engineers_by_required_skills を閾値ベースに書き換え
  - Counter方式に変更
  - min_match = max(1, ceil(0.5 * len(resolved)))
  - top-100キャップ追加
  - import math, Counter 追加

- [x] T2: config.py に定数追加
  - SKILL_MATCH_THRESHOLD = 0.5
  - MAX_CANDIDATES_BEFORE_JUDGE = 100

- [x] T3: テスト追加 (tests/test_retrieval_fix.py)
  - test_partial_match_passes (5中3 → 含まれる)
  - test_below_threshold_excluded (5中1 → 除外)
  - test_min_one_match (2中1 → 含まれる)
  - test_no_resolved_skills_returns_empty
  - test_candidate_cap_at_100
  - test_empty_engineers_returns_empty
  - test_backward_compat_full_match (全一致 → 当然含まれる)

- [x] T4: 既存テスト全PASS確認
  - cd matching_v3 && python -m pytest tests/ -v
  - 新テスト7件PASS、既存8件はPre-existing failures（Phase2A0変更と無関係）
  - test_task_an_speedup.py: 旧AND動作テスト2件を新ロジック期待値に更新

- [x] T5: 実データ検証スクリプト作成
  - scripts/validate_phase2a0.py 作成済み
  - 2026-06-26 実行: 20案件 avg_before=4.00 / avg_after=12.20 (目標>=3.0 OK)
  - 結果出力先: research_results/phase2a0_validation.md
