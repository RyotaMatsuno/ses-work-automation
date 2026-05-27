# TASKS: 入力元ラベル・所属会社名 実装チェックリスト

## Phase 1: Notionフィールド追加
- [ ] add_input_source_fields.py 作成・実行（エンジニアDB・案件DB両方）

## Phase 2: mail_pipeline.py (v5.1)
- [ ] get_input_source_label() 関数追加
- [ ] extract_affiliation() 関数追加（Claude AIで本文解析）
- [ ] register_project() に input_source・affiliation パラメータ追加
- [ ] register_engineer() に input_source・affiliation パラメータ追加
- [ ] main() で EMAIL_USER からラベル取得して渡す
- [ ] バージョンコメントを v5.1 に更新

## Phase 3: notify_line.py
- [ ] get_page_info() に input_source・affiliation 取得を追加
- [ ] empty_page_info() に input_source・affiliation の空値を追加
- [ ] build_project_message() に所属・入力元・⚡LINE案件プレフィックス追加
- [ ] エンジニアブロックに所属・入力元を追加
- [ ] result.jsonのループ前にLINE案件ソートを追加

## Phase 4: webhook_server.py
- [ ] MATSUNO_USER_ID / OKAMOTO_USER_ID 定数を追加
- [ ] get_line_source_label() 関数追加
- [ ] 案件/エンジニア登録時に input_source を Notion に渡す

## Phase 5: 動作確認
- [ ] add_input_source_fields.py を実行してNotionにフィールド追加確認
- [ ] mail_pipeline.py --dry-run 相当で動作確認
- [ ] notify_line.py --dry-run で通知文フォーマット確認
