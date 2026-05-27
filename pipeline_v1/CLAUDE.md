# CLAUDE.md — Phase1営業パイプライン 作業ルール

最終更新: 2026-05-25

## 作業ルール
- SPEC.mdとTASKS.mdを必ず最初に読む
- TASKS.mdを上から順番に実装し、完了したら[x]にチェック
- 1タスク完了ごとにTASKS.mdを更新する
- 既存ファイルを破壊しない
- 実装完了後は必ず動作確認コマンドを実行する

## 禁止事項
- TASKS.mdの順番を飛ばすこと
- 未完了のまま次タスクに進むこと
- ses_work/以下の既存ファイルを無断で修正すること
- 本番Notionデータを書き換えること（dry_run=Trueで開発）
- メール送信すること（dry_run=Trueで開発）

## 環境
- Python 3.12
- 作業ディレクトリ: C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1\
- .envパス: C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env
- NotionエンジニアDB: 343450ff-37c0-819d-8769-fb0a8a4ceeb1
- Notion案件DB: 343450ff-37c0-81e4-934e-f25f90284a3c
- credentialロード: from dotenv import dotenv_values; config = dotenv_values(".envのフルパス")

## 依存ライブラリ
- requests, python-dotenv, anthropic（インストール済み前提）
