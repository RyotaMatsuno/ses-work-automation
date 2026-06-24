# CLAUDE.md - auto_bug_watcher
最終更新: 2026-06-12

## 作業ルール
- 実装者はCursor（Claude Sonnet 4.6）。ジョブズは設計のみ。
- 3点セット（CLAUDE.md/SPEC.md/TASKS.md）を参照してから実装開始すること
- sys.stdout.reconfigure(encoding='utf-8', errors='replace') を全スクリプト冒頭に配置

## ディレクトリ構成
```
ses_work/auto_bug_watcher/
├── CLAUDE.md (このファイル)
├── SPEC.md
├── TASKS.md
├── watcher.py           # メインスクリプト
├── classifier.py        # GPT+Gemini並列診断
├── collectors/
│   ├── __init__.py
│   ├── log_collector.py
│   └── scheduler_collector.py
├── actions/
│   ├── __init__.py
│   ├── cursor_task_writer.py
│   ├── line_alerter.py
│   └── notion_logger.py
└── logs/                # 実行ログ・lockファイル置き場
```

## 依存ライブラリ
- agreement_checker: sys.path.insertで gate_checker 親ディレクトリを追加してimport
  例: sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
  from gate_checker.agreement_checker import run_dual_review, AgreementDecision
- config/.env: 全APIキーはここから_load_env()で読む（agreement_checker._load_env()流用可）
- 外部ライブラリ: 標準ライブラリのみ使用（urllib, json, os, datetime, threading等）

## 禁止事項
- requests, httpx等のサードパーティライブラリは使わない（urllib使用）
- NOTION_API_KEYをコードにハードコードしない
- タイムアウトなしのAPI呼び出しは禁止（timeout=45秒を設定）
- --dry-run以外でのLINE送信テストは禁止

## Notion API注意
- ヘッダー: Notion-Version: 2022-06-28 (必須)
- query-data-sourceは失敗する環境のため、直接REST APIを使う
- POST https://api.notion.com/v1/pages でレコード登録

## CostGuard（独自管理）
- auto_bug_watcher/logs/cost_today.json で当日コストを管理
- {"date": "YYYY-MM-DD", "usd": 0.0} の形式
- COST_DAILY_LIMIT_BUGWATCH環境変数（デフォルト1.0USD）を超えたらGPT診断スキップ
- GPT-4o診断コスト概算: 入力2000tokens + 出力500tokens ≈ $0.005/件

## エンコーディング（Windows必須）
- 全スクリプト冒頭: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
- ファイル書き込み: encoding='utf-8'
- 日本語パスはos.getcwd()等で取得し、直接文字列に書かない

## 完了条件
python auto_bug_watcher/watcher.py --dry-run
→ 収集ログ件数・診断分類・アクション分岐先がコンソールに出力されること
→ auto_bug_watcher/logs/YYYYMMDD.log が生成されること
→ 0件でもエラーなく終了すること（returncode 0）
