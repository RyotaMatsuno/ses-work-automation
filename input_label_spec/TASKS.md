# TASKS.md - 入力元ラベル・所属会社名

- [ ] 1. mail_pipeline.py: get_source_label(from_addr)関数を追加
- [ ] 2. mail_pipeline.py: AI所属会社名抽出をメール本文から実装（取れなければ空欄）
- [ ] 3. mail_pipeline.py: エンジニア/案件Notion登録時に入力元・所属会社名を追記
- [ ] 4. webhook_server.py: user_idでラベル付与（松野LINE/岡本LINE）、Notion登録に入力元追記
- [ ] 5. notify_line.py: LINE通知文に入力元・所属会社名を追加、LINE案件に⚡付けて先頭ソート
- [ ] 6. py_compile 3ファイル確認
- [ ] 7. get_source_label単体テスト（松野メール/岡本メール/共通メールの3ケース）
