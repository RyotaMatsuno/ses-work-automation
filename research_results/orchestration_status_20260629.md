# Orchestration Status — 2026-06-29

実行計画: `pending_tasks/00_ORCHESTRATION_20260629.md`

## 1. engineer_extractor (Phase A-2) — ✅ 完了

- E2〜F5 完了、ゲート F1/F3/F4 全 PASS
- 詳細: `research_results/engineer_db_gate_report_20260629.md`
- pytest: 65 passed

## 2. matching_v3 Phase 5 (Phase A-1) — ✅ 完了

v5.1 実装済み:
- 粗利判定3値化（推定単価のみでNG禁止→REVIEW）
- 未知スキル必須/尚可分離
- 並行スコア欠損→REVIEW
- `get_active_engineers()` fail-open
- `judge_version="v5.1"` 記録

検証:
- `py_compile` matcher.py / notion_client.py — OK
- `tests/test_matcher.py` + `tests/test_notion_client.py` — **80 passed**
- 全suite: 263 passed / 9 failed（skill_aliases辞書の既存不整合: C/C言語、pl/sql→SQL、LLM→生成AI 等。Phase5専用テストは全PASS）

## 3. matching_v3 Phase 3 (Phase B) — ✅ 完了

- `TASKS_phase3.md` 全チェック済み
- `py_compile` structurer.py / outlook_to_notion.py / ai_extractor.py — OK

## 4. cost_guard_v2 (Phase C) — ⏸ 一部保留

完了:
- Phase 0〜8 実装・テスト済み
- Phase 7.1〜7.4, 7.6, 7.7 完了

保留（松野確認必須）:
- **7.5** `line_webhook/line_bridge.py` — ローカル CostGuard 使用中、Cloud Run再デプロイ要
- **Phase 9** 実装レビュー（GPT-5.4壁打ち）
- **Phase 10** 本番デプロイ

## 次のアクション

1. 松野確認後: line_bridge → `cost_guard.allowed()` 置換 + Cloud Run デプロイ
2. Phase 9 レビュー取得 → GO 後 Phase 10 デプロイ
3. （任意）matching_v3 回帰テスト9件 — skill_aliases.json の C/LLM/plsql マッピング整理
