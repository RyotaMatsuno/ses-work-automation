# Phase 2A1: ステータス管理 + Active Pool — TASKS.md

- [x] T1: scripts/populate_status.py 作成
  - メモキーワード分析で稼働状況を判定
  - dry-run モード（--dry-run）でレポート出力
  - apply モード（--apply）でNotion更新
  - 出力: research_results/status_populate_report.md

- [x] T2: notion_client.py に update_engineer_status 追加
  - page_id, status を受け取り稼働状況selectを更新
  - rate limit考慮（既存_patch_page_with_rate_limit使用）

- [x] T3: notion_client.py の get_active_engineers を修正
  - 既存: 提案対象フラグ=True → staleness filter
  - 変更: 提案対象フラグ=True → Notionフィルタで稼働状況≠"稼働中"も追加 → staleness filter
  - 注意: 空欄（未設定）は除外しない

- [x] T4: テスト追加 (tests/test_status_filter.py)
  - test_status_excluded
  - test_blank_status_included
  - test_available_included
  - test_adjusting_included

- [x] T5: 既存テスト全PASS確認
  - cd matching_v3 && python -m pytest tests/ -v
  - ※8件の既存失敗は2A1実装前から存在（無関係）

- [ ] T6: dry-run実行してレポート確認（松野が--apply実行前に確認）
