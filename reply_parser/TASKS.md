# TASKS.md - 返信自動解析システム

## タスクリスト

- [x] 1. reply_parser/reply_parser.py 新規作成
       - config/.envからcredential読み込み
       - ses-mail MCPではなくNotion APIで直接エンジニアDB参照
       - Claude haiku APIで並行ステータス・スキル○×を抽出するprompt設計
       - 並行スコア計算ロジック（判断マニュアルv3 §5準拠）
       - 提案可否判定ロジック
- [x] 2. --dry-runオプション実装（Notion書き込みをスキップ）
- [x] 3. smoke test用サンプルメール本文をtest_data/sample_reply.txtとして作成
- [x] 4. python reply_parser/reply_parser.py --dry-run --sample でサンプル解析動作確認
- [x] 5. py_compile reply_parser/reply_parser.py 確認
- [x] 6. TASKS.mdを完了チェック
