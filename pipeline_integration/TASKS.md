# TASKS.md - SES Pipeline 全機能統合 実装チェックリスト

## 実装順序（この順番で実施すること）

- [x] TASK-1: drive_uploader.py 新規作成（SPEC-A）
  - upload_to_drive(file_path) -> str 実装
  - extract_spreadsheet_url(text) -> str|None 実装
  - DRY_RUN=1 時はダミーURL返却
  - 単体テスト: python drive_uploader.py でテストファイルをアップロード
  - 動作確認結果: DRY_RUN=1 python drive_uploader.py でダミーURL返却を確認

- [x] TASK-2: send_counter.json 初期化
  - config/send_counter.json を {"matsuno": 0, "okamoto": 0} で作成
  - 動作確認結果: config/send_counter.json 作成済み

- [x] TASK-3: mail_pipeline/mail_pipeline.py 修正（SPEC-B-1: 受信処理）
  - 既存バックアップ確認: mail_pipeline/mail_pipeline.py.bak_0526 が存在すること
  - Message-ID保存の追加
  - 案件情報原文・人員情報原文の保存追加
  - 添付ファイル保存処理（attachments/配下）
  - Excelファイルのdrive_uploader呼び出し
  - スプレッドシートURL抽出処理
  - 動作確認結果: 構文チェックで import/構文エラーなしを確認

- [x] TASK-4: mail_pipeline/mail_pipeline.py 修正（SPEC-B-2: 送信処理）
  - Fromアドレス切り替えロジック実装
  - send_counter.jsonの交互管理実装
  - In-Reply-Toヘッダー付与
  - 本文末尾への引用ブロック追加
  - MIMEMultipartへの添付ファイル処理
  - 動作確認結果: 構文チェックで送信ヘルパーの構文エラーなしを確認

- [x] TASK-5: matching_v2/notify_line.py 修正（SPEC-C）
  - 既存バックアップ確認: matching_v2/notify_line.py.bak_0526 が存在すること
  - 提案可能通知のフォーマット変更（案件・人員全文＋DriveリンクURL＋仕入単価）
  - 動作確認結果: DRY_RUN起動確認で通知処理の構文エラーなしを確認

- [x] TASK-6: line_webhook/webhook_server.py 修正（SPEC-D）
  - 既存バックアップ確認: line_webhook/webhook_server.py.bak_0526 が存在すること
  - 催促コマンドのパース・メール送信処理追加
  - 進捗確認コマンドの処理追加
  - 動作確認結果: 構文チェックでコマンド追加部分の構文エラーなしを確認

- [x] TASK-7: 統合dry_runテスト
  - DRY_RUN=1 python mail_pipeline/mail_pipeline.py でエラーなく動作すること
  - DRY_RUN=1 python matching_v2/notify_line.py でエラーなく動作すること
  - 動作確認結果: DRY_RUN=1 で実行確認済み（詳細は完了報告）

## 完了条件
- 全TASKのチェックボックスが埋まっていること
- dry_runテストがエラーなく通ること
- 各TASKの末尾にコメントで動作確認結果を記載すること
