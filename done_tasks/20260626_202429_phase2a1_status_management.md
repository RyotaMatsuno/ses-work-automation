【Cursor作業指示】
対象ディレクトリ: ses_work/matching_v3/
作業内容: エンジニアDBの稼働状況フィールド投入 + Active Poolフィルタリング

参照ファイル:
- matching_v3/SPEC_phase2a1.md（仕様書 — 必ず最初に読む）
- matching_v3/TASKS_phase2a1.md（チェックリスト）
- matching_v3/CLAUDE_phase2a1.md（作業ルール）

完了条件:
1. scripts/populate_status.py が作成され dry-run で正常動作
2. notion_client.py に update_engineer_status が追加
3. get_active_engineers() が稼働状況="稼働中"を除外（空欄は含む）
4. tests/test_status_filter.py が作成され全PASS
5. 既存テスト全PASS
6. TASKS_phase2a1.md のチェックリスト全完了

質問がある場合: Claude.aiチャットに貼り付けて確認
