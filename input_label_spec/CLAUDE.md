# CLAUDE.md - 入力元ラベル・所属会社名

## 禁止事項
- 既存の送信ロジックを壊さない（追記のみ）
- Notionフィールドが存在しない場合はスキップ（エラーにしない）
- LINE user_idをログに出力しない

## コーディングルール
- Python 3.11
- エラーは握りつぶさずログに書く
- Notionフィールド追加は行わない（既存フィールドへの書き込みのみ）

## 対象ディレクトリ
- ses_work/mail_pipeline/mail_pipeline.py
- ses_work/line_webhook/webhook_server.py
- ses_work/matching_v2/notify_line.py
