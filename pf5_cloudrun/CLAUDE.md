# CLAUDE.md - Phase5 Cloud Run LLM_KILL実装

## 作業ルール
- 変更するファイルは `line_webhook/webhook_server.py` と `line_webhook/skill_extractor.py` のみ
- 既存ロジックへの影響を最小限にする（LLM_KILLフラグの追加のみ）
- 変更箇所は必ずコメントで `# [Phase5]` を付ける
- syntax確認を必ず実施すること

## 禁止事項
- 既存の分類ロジック・通知ロジックへの手を加えること
- LLM_KILL以外の新機能追加
- Dockerfileの変更（不要）
- requirements.txtの変更（不要）
- gcloud deployは行わない（ジョブズが手動で確認後に実施）

## ファイルパス
- 作業対象: `C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\`
- webhook_server.py: 86,115 bytes（LLM呼び出し: Line166 call_claude, Line1558 analyze_skill_sheet）
- skill_extractor.py: 8,243 bytes

## syntax確認コマンド
```
python -c "import py_compile; py_compile.compile('line_webhook/webhook_server.py', doraise=True); py_compile.compile('line_webhook/skill_extractor.py', doraise=True); print('ALL OK')"
```
