# CLAUDE.md - pdca_monitor

## 目的
松野PCの操作ログ（5分間隔）を収集し、毎週金曜18:00に週次PDCAレポートをLINE・Notionへ送る。

## 作業ルール
- Python 3.x / UTF-8
- `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` を各エントリポイント冒頭に必須
- `.env` は `ses_work/config/.env` から読む
- 日本語パスを cwd / schtasks 引数に直接渡さない（bat は `%~dp0` で解決）
- collector / ocr は LLM 不使用（CostGuard 不要）
- reporter の Claude API 呼び出しは **必ず** `common.ledger.can_spend` + `record` を通す
- エラーは握りつぶさずログに記録して継続（collector）
- パスワード・APIキー・クレジットカード番号は DB / ログに平文保存しない（ocr.py でマスク）

## 禁止事項
- CostGuard なしで Claude API を呼ぶ
- 松野にファイル探索をさせる構成
- 本番 Notion DB（エンジニア・案件）への書き込み

## ファイル配置
- 実装: `ses_work/pdca_monitor/`
- DB: `pdca_monitor/data/activity.db`
- スクショ: `pdca_monitor/screenshots/{YYYY-MM-DD}/`（7日で自動削除）
- ログ: `pdca_monitor/logs/pdca_YYYYMMDD.log`

## スケジュール
- collector: 平日 08:00〜20:00、5分おき（weekday_guard + 時刻ガード）
- reporter: 毎週金曜 18:00（weekday_guard 経由）
