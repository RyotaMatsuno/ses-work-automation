# TASKS.md - pdca_monitor 実装チェックリスト

## Phase 1: 基盤
- [x] CLAUDE.md / SPEC.md / TASKS.md
- [x] db.py（スキーマ・週次集計・クリーンアップ）
- [x] ocr.py（Tesseract・マスク）

## Phase 2: 収集
- [x] collector.py（ウィンドウ・スクショ・OCR・DB保存）
- [x] スクショ7日削除・DB30日削除
- [x] 平日 08:00-20:00 ガード

## Phase 3: レポート
- [x] reporter.py（データ集約・Claude・LINE・Notion）
- [x] CostGuard（common.ledger）
- [x] --mock モード

## Phase 4: 運用
- [x] setup_scheduler.py
- [x] run_collector.bat / run_reporter.bat
- [x] py_compile pass
- [x] モック動作確認
- [x] Windowsタスクスケジューラ登録

## 依存（手動）
- [ ] Tesseract OCR 本体インストール（未導入時は OCR スキップで動作）
