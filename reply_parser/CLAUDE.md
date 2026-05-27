# CLAUDE.md - 返信自動解析システム

## 禁止事項
- 既存のmail_pipeline.py・matching_v2・notify_line.pyを改変しない
- 送信系処理（メール送信・LINE送信）をこのスクリプト内で実行しない
- 解析結果はNotion DBに書き込むのみ

## 作業ルール
- credentialはconfig/.envからdotenv_valuesで読み込む
- py_compile確認必須
- ログはlogs/reply_parser.logに出力（print flush=True）
- 文字コードはutf-8

## 対象ファイル
- sales_pipeline/step3_parse.py（既存・改修）
- reply_parser/reply_parser.py（新規）
- reply_parser/SPEC.md / TASKS.md（設計書）
