# TASKS.md - 入金確認自動化

## タスクリスト

- [x] 1. freee/payment_checker.py 新規作成
       - freee_auth/token_manager.pyのget_headers()でトークン取得
       - freee API /api/1/invoices で発行済み請求書一覧取得（payment_status含む）
       - 支払期日超過チェック（today > payment_due_date かつ unpaid）
       - logs/payment_notified.json で通知済みフラグ管理（重複防止）
       - 未入金アラートメッセージを組み立て
       - 松野のLINE Push API送信（LINE_CHANNEL_ACCESS_TOKEN + MATSUNO_LINE_USER_ID）
- [x] 2. --dry-runオプション実装（LINE送信スキップ）
- [x] 3. Windowsタスクスケジューラ登録スクリプト作成
       - タスク名: freee_payment_check
       - 毎月10日・20日・28日 08:00実行
- [x] 4. python freee/payment_checker.py --dry-run で動作確認
- [x] 5. py_compile freee/payment_checker.py 確認
