# SPEC.md - PC操作ログ収集 + 週次PDCAレポート

バージョン: 1.0  
作成日: 2026-06-09

## 1. 概要

| コンポーネント | 実行タイミング | LLM |
|---|---|---|
| collector.py | 平日 08:00-20:00 / 5分 | なし |
| reporter.py | 金曜 18:00 | Sonnet 4.6（CostGuard必須） |

## 2. collector.py

収集項目: タイムスタンプ、アプリ名、ウィンドウタイトル、スクリーンショット、OCRテキスト

- アクティブウィンドウ: win32gui（優先）/ pygetwindow（フォールバック）
- スクショ: Pillow、JPG品質50、`screenshots/{YYYY-MM-DD}/`
- OCR: pytesseract。空テキストは DB に ocr_text=NULL で保存
- 機密マスク: パスワード・クレカっぽい文字列を正規表現で `[MASKED]`
- 7日超のスクショフォルダ自動削除
- DB レコードは 30日超で cleanup_old_records

## 3. db.py

`activity_log` テーブル。`get_weekly_summary(start, end)` で以下を返す:
- app_name 別使用時間（分、5分間隔前提）
- window_title TOP10
- OCR キーワード TOP20（単純頻度）

## 4. reporter.py

データソース:
1. db.py 週次サマリー
2. Notion AI作業キュー（done / blocked 件数）
3. mail_pipeline ログ（週次処理回数）
4. matching_v3 ログ（週次マッチング件数）

出力:
- LINE push（MATSUNO_LINE_USER_ID）
- Notion 週次ページ（SESナレッジWiki `353450ff-37c0-8145-9e3e-d80c8c8ed594` 配下）

`--mock` 時は API 送信せずローカル検証のみ。

## 5. setup_scheduler.py

| タスク名 | スケジュール |
|---|---|
| jobz_pdca_collector | 平日 MON-FRI / 5分間隔 / 08:00-20:00 |
| jobz_pdca_reporter | 毎週金曜 18:00 |

weekday_guard.py 経由の bat を `/tr` に登録。

## 6. 人間確認ゲート

- 本番 LINE 送信・Notion ページ作成は reporter の定常実行（松野承認済みフロー）
- `--mock` は開発検証専用
