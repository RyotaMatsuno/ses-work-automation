# CLAUDE.md - LINE通知スクリプト作業ルール

## 禁止事項
- 既存ファイルの削除・上書き（ses_work配下の他システム）
- LINE Messaging API以外への外部通信
- 本番のLINEトークンをログに出力すること
- 例外を握りつぶすこと（必ずraiseかログ出力）

## 環境変数の読み込み
- `ses_work/config/.env` から dotenv で読み込む
- 変数名:
  - MATSUNO_LINE_USER_ID
  - LINE_CHANNEL_ACCESS_TOKEN (松野チャンネル)
  - OKAMOTO_LINE_USER_ID
  - OKAMOTO_LINE_CHANNEL_ACCESS_TOKEN (岡本チャンネル)

## コーディングルール
- Python 3.10以上対応
- 外部ライブラリ: requests, python-dotenv のみ使用
- 文字コード: UTF-8
- ログは print() で標準出力へ（タイムスタンプ付き）
- LINE Messaging APIのエンドポイント: https://api.line.me/v2/bot/message/push

## ファイル構成
- notify_line.py: メイン通知スクリプト
- SPEC.md, TASKS.md, CLAUDE.md: 設計ドキュメント（編集不要）
