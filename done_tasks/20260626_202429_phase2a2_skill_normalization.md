【Cursor作業指示】
対象ディレクトリ: ses_work/matching_v3/
作業内容: エンジニアDBの正規化スキルフィールド投入

参照ファイル:
- matching_v3/SPEC_phase2a2.md（仕様書 — 必ず最初に読む）
- matching_v3/TASKS_phase2a2.md（チェックリスト）
- matching_v3/CLAUDE_phase2a2.md（作業ルール）

完了条件:
1. scripts/normalize_all_skills.py が作成され dry-run で正常動作
2. tests/test_skill_normalize.py が作成され全PASS
3. 既存テスト全PASS
4. dry-runレポートでサンプル品質確認済み
5. TASKS_phase2a2.md のチェックリスト全完了

質問がある場合: Claude.aiチャットに貼り付けて確認
