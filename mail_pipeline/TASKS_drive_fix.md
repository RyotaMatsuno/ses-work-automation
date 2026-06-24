# TASKS.md - Drive URL PATCH修正

- [x] 1. バックアップ作成: mail_pipeline.py → mail_pipeline.py.bak_drive_fix
- [x] 2. L1034-1036: rich_text → url型に修正（PROJECT_DB）
- [x] 3. L1084-1087: rich_text → url型に修正（ENGINEER_DB）
- [x] 4. L1360-1362: rich_text → url型に修正（PROJECT_DB PATCH後）
- [x] 5. L1452-1455: rich_text → url型に修正（ENGINEER_DB PATCH後）
- [x] 6. add_rich_text_if_exists でDriveリンクURLを書いている全箇所を確認・修正
- [x] 7. 構文チェック: python -c "import ast; ast.parse(open('mail_pipeline.py').read())"
- [x] 8. TASKS.md を全て [x] に更新
