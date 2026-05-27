# TASKS.md - LINE通知スクリプト実装チェックリスト

## タスク一覧

- [ ] 1. notify_line.py の骨格作成（argparse, dotenv読み込み）
- [ ] 2. result.json 読み込み処理
- [ ] 3. メッセージ整形処理（案件単位、上位3名、5000字分割）
- [ ] 4. LINE Messaging API Push送信処理（松野・岡本）
- [ ] 5. --dry-run オプション実装
- [ ] 6. エラーハンドリング（ファイルなし・API失敗・環境変数未設定）
- [ ] 7. 動作確認（dry-runで出力確認）

## 完了条件
- `python notify_line.py --dry-run` を実行してコンソールに整形済みメッセージが出力される
- エラーなく returncode:0 で終了する
