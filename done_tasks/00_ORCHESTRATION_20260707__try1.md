# ORCHESTRATION 2026-07-07

| # | タスク | 依存 | 並列可否 |
|---|--------|------|----------|
| 1 | 20260707_000000_canonical38_zero_ref_delete.md | なし | 並列可 |
| 2 | 20260707_000001_git_secret_scan_hook.md | なし | 並列可 |

- 両タスク独立。順序任意・並列実行可。
- 両タスクとも完了後ゲートは7/7以降に実行（7/6はゲート日次上限30/30到達）。
- タスク1はskill_aliases.jsonバックアップ必須・実行時参照再検証必須（明朝バッチ後の参照ズレ対策）。


## RETRY 1 REASON
target_file not found: 
