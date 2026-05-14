# CLAUDE.md - メール添付スキルシート自動取り込みシステム

## プロジェクト概要
TERRA共通アドレスに届いた添付スキルシート（Excel/PDF/Word）を
Claude APIで解析してNotionエンジニアDBに自動登録するシステム。

## 技術スタック
- Python 3.12
- imaplib（メール受信・添付取得）
- openpyxl（Excel読み取り）
- pdfplumber（PDF読み取り）
- python-docx（Word読み取り）
- anthropic SDK（Claude API - ファイル解析・構造化抽出）
- requests（Notion API）
- python-dotenv（環境変数）

## 設定ファイル
- 環境変数: `C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env`
- 既存キー: NOTION_API_KEY / NOTION_ENGINEER_DB_ID / ANTHROPIC_API_KEY
- IMAP: OUTLOOK_IMAP_SERVER / OUTLOOK_IMAP_PORT / OUTLOOK_EMAIL / OUTLOOK_PASSWORD

## ディレクトリ構成
```
ses_work/mail_attachment_importer/
  CLAUDE.md            # このファイル
  SPEC.md              # 仕様書
  TASKS.md             # タスクリスト
  importer.py          # メインスクリプト（定期実行エントリポイント）
  mail_fetcher.py      # IMAP接続・添付取得モジュール
  file_parser.py       # Excel/PDF/Word→テキスト変換モジュール
  ai_extractor.py      # Claude APIで構造化データ抽出モジュール
  notion_writer.py     # Notion登録・重複チェックモジュール
  processed_ids.json   # 処理済みメールUID管理（重複実行防止）
  importer.log         # 実行ログ
```

## 禁止事項
- processed_ids.jsonを確認せずに同一メールを2回処理しない
- Notion登録前の重複チェック（名前照合）を省略しない
- エラー1件で全体を止めない（スキップしてログ記録して継続）
- 添付ファイルをローカルに永続保存しない（処理後は削除）
- TASKS.mdのチェックボックスを完了ごとに必ず更新する

## Notionスキルマッピング（既存選択肢に厳密に合わせること）
Java / Python / PHP / JavaScript / TypeScript / C# / Node.js / React /
AWS / インフラ / PostgreSQL / Oracle / Vue.js / MySQL / Swift / Azure /
Linux / Go / Ruby / Docker / MongoDB / Spring
