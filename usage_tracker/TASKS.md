# TASKS.md - 実装チェックリスト

## 実装順序（上から順に完了させること）

- [x] 1. `usage_tracker/__init__.py` 作成（空ファイル）
- [x] 2. `usage_tracker/cost_calculator.py` 作成（モデル別単価・トークン→USD→円変換）
- [x] 3. `usage_tracker/cost_logger.py` 作成（log_cost()関数・cost_log.jsonlへの追記）
- [x] 4. `usage_tracker/notion_writer.py` 作成（Notion DB作成・レコード書き込み）
- [x] 5. `usage_tracker/usage_tracker.py` 作成（日次集計メイン・Notion書き込み・アーカイブ）
- [x] 6. `usage_tracker/setup_scheduler.py` 作成（タスクスケジューラ登録）
- [x] 7. `usage_tracker/run_usage_tracker.bat` 作成
- [x] 8. `matching_v2/skill_judge.py` に log_cost() 実装済み（既存実装確認）
- [x] 9. `mail_pipeline/mail_pipeline.py` に log_cost() 実装済み（既存実装確認）
- [x] 10. `usage_tracker/usage_tracker.py` 単体実行 → Notion書き込み確認済み（2026-05-26）

## 完了確認
- [x] cost_log.jsonl にレコードが書き込まれること
- [x] Notion「コスト管理DB」にレコードが作成されること（2026-05-25 matching_v2, mail_pipeline）
- [x] タスクスケジューラに「usage_tracker_daily」が登録されること（毎日09:05）
