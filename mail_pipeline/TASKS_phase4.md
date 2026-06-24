# Phase4 TASKS

- [ ] mail_pipeline.py を mail_pipeline.py.bak_phase4 にコピー（バックアップ）
- [ ] common.ledger のimportを先頭に追加（_LEDGER_OK フラグ付き）
- [ ] hashlib importを追加
- [ ] fetch_emails_from_account: Message-IDなしメールのdedup key を sha1ハッシュに変更
- [ ] call_claude(): 冒頭のコストゲートをledger接続に変更
- [ ] call_claude(): API成功後にledger_record()を追加
- [ ] classify_email_v2/send_batch: batch結果処理ループにledger_record()を追加（batch_requestsとsecond_extract_requestsの両方）
- [ ] py_compile で構文確認
