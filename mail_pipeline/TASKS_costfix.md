# TASKS_costfix.md
# mail_pipeline コスト暴走修正 実装チェックリスト

## タスク一覧

- [x] TASK-1: バックアップ作成
  - mail_pipeline.py → mail_pipeline.py.bak_costfix にコピー

- [x] TASK-2: 定数変更 (Fix 1)
  - FETCH_LIMIT = 2000 → 200
  - PROCESS_LIMIT = 2000 → 50

- [x] TASK-3: fetch_emails_from_account に SINCE フィルタ追加 (Fix 1)
  - 引数に `since_days=7` を追加
  - imap.search の ALL を SINCE {7日前} に変更
  - fetch_recent_emails からの呼び出し側も引数を渡すよう修正

- [x] TASK-4: processed_ids 上限ロジック修正 (Fix 2)
  - `if len(ids_list) > 2000: ids_list = ids_list[1000:]` を
    `if len(ids_list) > 10000: ids_list = ids_list[-10000:]` に変更

- [x] TASK-5: finally 節で save_processed_id 保証 (Fix 3)
  - main() の `for i, em in enumerate(target_emails):` ループを
    try/except/finally で囲む
  - finally に `save_processed_id(msg_id, processed)` を追加
  - msg_id の初期化は try ブロックの外で行う

- [x] TASK-6: 日次コストガード追加 (Fix 4)
  - 定数 DAILY_COST_LIMIT_USD = 2.0 を追加
  - get_today_cost_usd() 関数を追加
  - call_claude() 先頭にガード処理を追加

- [x] TASK-7: 動作確認
  - `python -m py_compile mail_pipeline.py` で構文チェック
  - `DRY_RUN=1 python mail_pipeline.py` で起動確認
  - ログに "全て処理済み" or 正常起動ログが出ることを確認
  - 結果を check_costfix_result.txt に書き出す
