# TASKS.md - ses-mail MIME添付対応

- [ ] 1. mail_mcp/mail_server.pyの send_email 関数に attachments パラメータを追加
- [ ] 2. MIMEMultipartでbase64デコード→添付するロジックを実装
- [ ] 3. py_compile mail_mcp/mail_server.py → エラーなし確認
- [ ] 4. 既存のsend_email呼び出しが動作すること（attachments=Noneのデフォルト動作確認）
