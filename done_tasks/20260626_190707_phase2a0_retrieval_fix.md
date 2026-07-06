【Cursor作業指示】
対象ディレクトリ: ses_work/matching_v3/
作業内容: filter_engineers_by_required_skillsのAND交差ロジックを閾値ベースに修正

参照ファイル:
- matching_v3/SPEC_phase2a0.md（仕様書 — 必ず最初に読む）
- matching_v3/TASKS_phase2a0.md（チェックリスト）
- matching_v3/CLAUDE_phase2a0.md（作業ルール）

完了条件:
1. filter_engineers_by_required_skills が閾値ベース（50%以上）に変更されている
2. config.py に SKILL_MATCH_THRESHOLD と MAX_CANDIDATES_BEFORE_JUDGE が追加されている
3. tests/test_retrieval_fix.py が作成され全PASS
4. 既存テスト全PASS（python -m pytest tests/ -v）
5. TASKS_phase2a0.md のチェックリストが全完了

質問がある場合: Claude.aiチャットに貼り付けて確認
