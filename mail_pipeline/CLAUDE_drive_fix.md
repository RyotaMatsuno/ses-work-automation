# CLAUDE.md - mail_pipeline Drive URL PATCH修正

## 作業ルール
- mail_pipeline/mail_pipeline.py のみ修正
- バックアップを先に作成すること: mail_pipeline.py.bak_drive_fix
- 変更行は最小限。ロジック変更禁止。

## 禁止事項
- processed_ids.json の削除・変更
- スケジューラの操作
- 他ファイルへの変更
- 新機能追加

## 完了条件
- Notion PATCH時に "Drive_URL" または "DriveリンクURL" フィールドをurl型で書き込む
- rich_text型で書き込もうとしている箇所を全てurl型に修正
- エラー時もprocessed_idは必ず保存してスキップ（現状維持）
