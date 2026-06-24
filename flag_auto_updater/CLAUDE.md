# CLAUDE.md - flag_auto_updater

## 事業文脈
SES人材紹介事業。エンジニアDBの「提案対象フラグ」を除外ルールに基づき自動判定・自動更新するシステム。

## 作業ルール
- 実装言語: Python 3.x
- 文字コード: UTF-8（ファイル書き込み時は必ずencoding='utf-8'）
- 日本語パス（デスクトップ等）はcwd/コマンドに直接渡さない
- .envはses_work/config/.envから読む（python-dotenvまたは手動parse）
- Notionアクセスは REST API直叩き（notion-clientライブラリ不使用）
- CostGuardなしでLLMを呼び出さない（本スクリプトはLLM不使用なので不要）
- エラーは握りつぶさず必ずログに出す
- sys.stdout.reconfigure(encoding='utf-8', errors='replace') をスクリプト冒頭に必ず入れる

## 禁止事項
- Notionの既存プロパティを削除しない
- エンジニアのページ自体を削除しない
- フラグ更新以外のプロパティを変更しない
- LLMによる判定（gpt/claude API呼び出し）は行わない（ルールベースのみ）

## ファイル配置
- 実装先: ses_work/flag_auto_updater/
- entrypoint: ses_work/flag_auto_updater/run_flag_updater.py
- ログ出力先: ses_work/flag_auto_updater/logs/flag_updater_YYYYMMDD.log
