# CLAUDE.md - usage_tracker 作業ルール

## 禁止事項
- CLAUDE.md / SPEC.md / TASKS.md を書き換えない
- .env を直接編集しない
- 既存の mail_pipeline.py / matching_v2/ には触らない（log_cost()追加のみ可）
- Notion DB（エンジニアDB・案件DB）には書き込まない（コストDBのみ操作）
- print以外のログ出力ライブラリを使わない（標準ライブラリのみ）

## 必須ルール
- credential は `config/.env` から dotenv_values で読み込む
- Notion REST API は requests で直接叩く（MCPは使わない）
- 全 print に flush=True を付ける
- 各スクリプトは `ses_work/usage_tracker/` に置く
- タスクスケジューラ用バッチは `ses_work/usage_tracker/run_usage_tracker.bat` に置く

## コーディング規約
- Python 3.10+
- 型ヒントを付ける
- try/except で全API呼び出しを囲む
- ログは `ses_work/usage_tracker/usage_tracker.log` に追記
