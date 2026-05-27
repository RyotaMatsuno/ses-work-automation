# CLAUDE.md — アポ取りシステム 作業ルール

最終更新: 2026-05-25

## 作業ルール
- SPEC.mdとTASKS.mdを必ず最初に読む
- TASKS.mdを上から順番に実装し、完了したら[x]にチェック
- 既存ファイルを破壊しない
- dry_run=True がデフォルト（本番送信しない）

## 禁止事項
- TASKS.mdの順番を飛ばすこと
- dry_run=Falseのままコードを書くこと
- ses_work/以下の既存ファイルを無断で修正すること
- 「断り」メモのある会社にメール送信すること

## 環境
- Python 3.12
- 作業ディレクトリ: C:\Users\ma_py\OneDrive\デスクトップ\ses_work\outreach_system\
- .envパス: C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env
- credentialロード: from dotenv import dotenv_values; config = dotenv_values(ENV_PATH)

## 依存ライブラリ
- requests, python-dotenv, smtplib（標準）, csv（標準）
