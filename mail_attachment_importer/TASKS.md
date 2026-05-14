# TASKS.md - メール添付スキルシート自動取り込みシステム

最終更新: 2026-05-14 (v3完了)

---

## Phase 0: 環境準備
- [x] 必要ライブラリインストール（openpyxl / pdfplumber / python-docx / anthropic / python-dotenv）← 完了 2026-05-13
- [x] processed_ids.json 初期化（空配列）
- [x] importer.log 初期化

## Phase 1: メール取得モジュール（mail_fetcher.py）
- [x] IMAP接続・認証（sessalesアドレス）
- [x] 未処理メールUID一覧取得（processed_ids.jsonと照合）
- [x] 添付ファイルありメールのみ抽出
- [x] 添付ファイルをメモリ上に取得（バイナリ）
- [x] 対応形式フィルタ（xlsx/xls/pdf/docx/doc）
- [x] スプレッドシートURL抽出（本文からGoogle Spreadsheet URLを検出）
- [x] タイムアウト対策（socket.setdefaulttimeout 30秒 + SINCE絞り込み）
- [x] v3書き換え完了・Content-Dispositionバグ修正済み（2026-05-14）

## Phase 2: ファイル解析モジュール（file_parser.py）
- [x] Excel読み取り（openpyxl）
- [x] PDF読み取り（pdfplumber）
- [x] Word読み取り（python-docx）
- [x] 単体テスト OK

## Phase 3: Claude API抽出モジュール（ai_extractor.py）
- [x] Claude API呼び出し実装
- [x] 単体テスト OK（2026-05-14 test_quick.py Step2確認）

## Phase 4: Notion登録モジュール（notion_writer.py）
- [x] 重複チェック・新規登録処理
- [x] テスト登録・削除確認（2026-05-13）
- [x] 統合テスト重複チェックOK（2026-05-14 test_quick.py Step3確認）

## Phase 5: スプレッドシート取得モジュール（sheet_fetcher.py）
- [x] Playwright方式でテキスト取得
- [x] ログイン必要なシートのスキップ
- [x] 単体テスト OK（2026-05-13）

## Phase 6: メインスクリプト統合（importer.py）
- [x] 全モジュール統合（パターンA/B/C対応）← v2書き換え完了（2026-05-13）
- [x] days_back=1 に修正（毎日実行想定）（2026-05-14）
- [x] 統合テスト実行 ← IMAP接続→Playwright→Claude API→Notion全パスOK確認（2026-05-14）
  - test_quick.py で軽量テスト完了（Step1/2/3全通過）
  - importer.py 実行確認: 3143件検出・処理開始確認（パターンB/Cで2件処理ログ確認）

## Phase 7: 定期実行設定
- [x] run_importer.bat 作成（2026-05-13）
- [x] Windowsタスクスケジューラに登録（毎朝8:00）← schtasks /create 成功（2026-05-14）
  - タスク名: jobz_importer
  - 次回実行: 2026/05/15 8:00:00
- [x] 動作確認 ← テスト実行でパイプライン全段階確認済み

---

## 完了サマリー（2026-05-14）
- 全パイプライン動作確認済み: IMAP → メール解析 → Playwright(スプレッドシート取得) → Claude API抽出 → Notion登録
- タスクスケジューラ登録済み（毎朝8:00自動実行）
- 初回本番実行: 2026/05/15 8:00

## 既知の注意事項
- sessalesのINBOXは1日3,000件超のメールが届く（ほぼ出回り配信）
- 1件あたり処理時間: 添付10秒 / スプレッドシート15秒程度
- タスクスケジューラ実行は添付・URL付きメール分のみ処理するため実際の件数は少ない
- 処理済みUIDはprocessed_ids.jsonで管理（再処理防止）
