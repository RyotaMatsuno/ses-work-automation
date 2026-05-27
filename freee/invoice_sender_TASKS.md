# TASKS.md - 請求書自動送付

## タスクリスト

- [ ] 1. freee/invoice_sender.py 新規作成
       - freee_auth/token_manager.pyのget_headers()でトークン取得
       - freee API /api/1/invoices で当月confirmed請求書一覧取得
       - /api/1/invoices/{id}/download でPDF取得（bytesで保存）
       - 送付先メールアドレスをNotionエンジニアDB or 案件DBから取得
       - ses-mail MCP相当のrequestsでメール送信（IMAP経由ではなくSMTP）
       - 送付完了をlogs/invoice_send.logに記録
- [ ] 2. --dry-runオプション実装（PDF取得まで実施・メール送信スキップ）
- [ ] 3. Windowsタスクスケジューラ登録スクリプト作成
       - タスク名: freee_invoice_send
       - 毎月1日 10:00実行（freee_auto_invoiceの1時間後）
- [ ] 4. python freee/invoice_sender.py --dry-run で動作確認
- [ ] 5. py_compile freee/invoice_sender.py 確認

## 注意
- 請求書がない月は正常終了（スキップ）
- PDFはtemp/に一時保存して送信後削除
- 送付先が不明の場合はLINEで松野に通知して手動対応を促す
