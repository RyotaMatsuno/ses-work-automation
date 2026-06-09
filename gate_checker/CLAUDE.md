# CLAUDE.md - gate_checker

## 事業文脈
SES人材紹介事業の開発ゲート制度を自動化する。ゲート①（設計レビュー）とゲート②（コードレビュー）をGPT-4oで実施し、GO/NGを機械的に判定する。

## 作業ルール
- 実装言語: Python 3.x
- 文字コード: UTF-8（ファイル書き込み時は必ず encoding='utf-8'）
- 日本語パス（デスクトップ等）はcwd/コマンドに直接渡さない
- .envは ses_work/config/.env から読む（python-dotenvまたは手動parse）
- 全LLM呼び出しは CostGuard（common/ledger.py）を通す
- レビュー用モデル: gpt-4o（OPENAI_API_KEY必須）
- エラーは握りつぶさず必ずログに出す
- sys.stdout.reconfigure(encoding='utf-8', errors='replace') をスクリプト冒頭に必ず入れる

## 禁止事項
- CostGuardなしでLLMを呼び出さない
- 日次10回上限を超えてAPIを呼び出さない
- レビュー対象以外のファイルを書き換えない（TASKS.mdのゲートフラグ更新のみ許可）
- APIキーをログやresults JSONに出力しない

## ファイル配置
- 実装先: ses_work/gate_checker/
- entrypoint: ses_work/gate_checker/gate_check.py
- 結果JSON: ses_work/gate_checker/results/gate_{phase}_{timestamp}.json
- 日次カウンタ: ses_work/gate_checker/results/daily_counter.json
