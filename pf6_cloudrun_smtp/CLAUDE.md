# CLAUDE.md - Phase6 Cloud Run SMTP環境変数設定

## 作業ルール
- 変更するファイルは `line_webhook/webhook_server.py` のみ
- send_email_via_callbackのアカウント設定辞書の環境変数キー名を修正する
- 既存の動作ロジックには一切手を加えない
- 変更箇所に `# [Phase6]` コメントを付ける
- syntax確認を必ず実施すること

## 禁止事項
- send_email_via_callback以外への変更
- gcloud deployは行わない（ジョブズが手動で確認後に実施）
- 新機能追加

## ファイルパス
- 作業対象: `C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py`

## syntax確認コマンド
```
python -c "import py_compile; py_compile.compile('line_webhook/webhook_server.py', doraise=True); print('OK')"
```
