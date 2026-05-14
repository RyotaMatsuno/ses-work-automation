# TASKS.md - LINE Webhook 自動化 実装チェックリスト

最終更新: 2026-05-08

## タスク一覧

- [x] CLAUDE.md 作成
- [x] SPEC.md 作成
- [x] TASKS.md 作成
- [x] **Task 1**: double_check.py を webhook_server.py に統合（Cloud Run環境対応）
- [x] **Task 2**: webhook_server.py の process_message() 案件フローにダブルチェック自動実行を組み込む
- [x] **Task 3**: LINE返信メッセージを「チェック済み結果 + 提案文（送信可能版）」形式に変更
- [x] **Task 4**: Cloud Runにデプロイ完了（revision: line-webhook-00003-2m5）
- [x] **Task 5**: ヘルスチェック確認 → OK
- [ ] **Task 6**: テストメッセージ送信で動作確認（岡本のWebhook設定完了後）
