# CLAUDE.md - SES Pipeline 全機能統合
# Codexへの作業ルール・禁止事項

## 基本ルール
- credentialは config/.env から dotenv_values で読む（ハードコード禁止）
- Drive tokenは config/drive_token.json から読む
- Notion REST APIは requests で直接叩く（MCPツール使用禁止）
- 既存ファイルは .bak_0602 を先に作ること
- print文には必ず flush=True を付ける
- 全て encoding='utf-8' を明示する
- DRY_RUN=1 環境変数でメール送信・Notion書き込み・Drive投稿をスキップする

## ディレクトリ構成
- メインパイプライン: mail_pipeline/mail_pipeline.py
- マッチング通知: matching_v2/notify_line.py
- Webhookサーバー: line_webhook/webhook_server.py
- Drive連携: drive_uploader.py (新規作成・ルート直下)
- 送信カウンター: config/send_counter.json (新規作成)
- 添付ファイル保存先: attachments/{notion_page_id}/

## 禁止事項
- MCP直接呼び出し
- credentialのハードコード
- サービスアカウント(google_credentials.json)をDriveアップロードに使用
- DRY_RUN=1 時の実際の送信・書き込み・API呼び出し
