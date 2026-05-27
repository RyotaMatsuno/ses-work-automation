# CLAUDE.md - attachment_importer

## 作業ルール
- SPEC.mdを必ず最初に読んでから実装を開始すること
- TASKS.mdのチェックリストを順番に実装し、完了したらチェックを入れること
- 1ファイル実装するごとに構文エラーがないことをpythonで確認すること（python -m py_compile）
- テストはtests/ディレクトリに置くこと
- ログは必ずflush=Trueで出力すること

## 禁止事項
- Notion APIへの直接書き込みテストは禁止（本番DBが汚れる）
- LINE送信は禁止
- .envファイルの中身をログに出力することは禁止
- SPEC.mdに記載のないフィールドをNotionに書き込まないこと

## 認証情報の読み込み
config/.envから dotenv_values で読み込む:
- NOTION_API_KEY
- ANTHROPIC_API_KEY（Claude API用）

## パス規則
- 作業ディレクトリは ses_work/
- スキルシート保存先: ses_work/attachment_importer/downloaded_files/
- ログ: ses_work/attachment_importer/import.log
- 失敗ログ: ses_work/attachment_importer/failed_imports.json

## Claude APIモデル
- モデル: claude-haiku-4-5-20251001（コスト最適化）
- max_tokens: 2000
- テキスト抽出・スキル判定の両方で使用
