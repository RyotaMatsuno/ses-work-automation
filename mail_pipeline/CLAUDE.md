# CLAUDE.md - メールパイプライン自動化PJ

最終更新: 2026-05-08

## プロジェクト概要
共通メール（sessales@terra-ltd.co.jp）を定期チェックし、
案件メール→Notion登録→マッチング→ダブルチェック→提案メール下書き生成
人材メール→Notion登録
を全自動で行うパイプライン。

## 技術スタック
- Python 3.12
- imaplib（IMAP接続）
- Anthropic API（Claude Sonnet 4）
- Notion API
- Windowsタスクスケジューラ（定期実行）

## ファイル構成
- `mail_pipeline.py` : メインパイプライン
- `../config/.env` : 環境変数
- `run_pipeline.bat` : タスクスケジューラ用バッチ
- `pipeline.log` : 実行ログ

## IMAP設定
- サーバー: mail65.onamae.ne.jp:993 SSL
- アカウント: sessales@terra-ltd.co.jp
- 重複防止: 既読メールはスキップ（未読のみ処理）

## 作業ルール
- 送信系は一切自動実行しない（下書き生成 + ログ出力のみ）
- ログは pipeline.log に追記
- エラーは握りつぶさずログに残す

## 禁止事項
- メール自動送信
- Notion既存レコードの上書き削除
- 送信確認なしの提案文送付
