# Phase 1 TASKS

## チェックリスト（完了したら[ ]→[x]に更新）

- [x] cost_guard.py を cost_guard.py.bak_phase1 にコピー（バックアップ）
- [x] 定数 DAILY_SOFT_LIMIT_USD = 6.0 を追加
- [x] 定数 DAILY_LIMIT_USD を 15.0 → 8.0 に変更
- [x] disable_tasks() に SES_MatchingV3, jobz_importer, SES_Outlook_9h, SES_Outlook_13h, SES_Outlook_18h を追加
- [x] kill_cloud_run() 関数を新規追加
- [x] main() を3段階制御（HARD/SOFT/HOURLY）に書き換え
- [x] py_compile で構文チェック → syntax_ok を確認
