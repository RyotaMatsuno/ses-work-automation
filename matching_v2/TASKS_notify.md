# TASKS_notify.md - notify_line.py 実装チェックリスト

## タスク一覧（この順番で実装すること）

- [ ] 1. notify_line.py の雛形作成（import・main関数の骨格）
- [ ] 2. config/.env の環境変数読み込み（load_env関数）
- [ ] 3. push_message関数の実装（LINE Push API呼び出し）
- [ ] 4. get_assignee関数の実装（NotionページIDから担当者取得）
- [ ] 5. result.jsonの読み込み処理
- [ ] 6. 案件担当者・エンジニア担当者の取得ロジック
- [ ] 7. 通知メッセージ生成関数（4ケース対応）
- [ ] 8. --dry-runフラグの実装（argparse）
- [ ] 9. メイン処理：candidates:[]案件のスキップ
- [ ] 10. メイン処理：4ケース分岐で通知送信
- [ ] 11. py_compile通過確認
- [ ] 12. --dry-runで実行してコンソール出力確認
