# auto_bug_watcher SPEC.md
最終更新: 2026-06-12

## 概要
SESシステム各コンポーネントのログ・タスクスケジューラを監視し、
エラーを自動検出してGPT-4o+Gemini並列診断→アクション分岐するバッチ。
毎日08:05にWindowsタスクスケジューラで自動実行。

## アーキテクチャ
```
watcher.py (main)
├── collectors/log_collector.py     # ログファイルからERROR行収集
├── collectors/scheduler_collector.py # タスクスケジューラ失敗タスク収集
├── classifier.py                   # GPT-4o+Gemini並列診断 (agreement_checker流用)
└── actions/
    ├── cursor_task_writer.py       # BUG_MINOR → pending_tasks/に指示書保存
    ├── line_alerter.py             # BUG_CRITICAL → LINE push送信
    └── notion_logger.py            # 全件をAI作業キューDBに登録
```

## 監視対象ログパス
- mail_pipeline/logs/
- matching_v3/logs/
- freee/logs/
- mail_attachment_importer/logs/
- gate_checker/logs/ (resultsも)
- line_webhook/logs/

## 正常パターン除外
- "No new emails"
- "weekday_guard skip"
- "No match found"
- "INFO" のみの行（ERRORを含まないもの）

## 診断分類
- BUG_CRITICAL: 即座に松野確認が必要なエラー（auth失敗、API quota枯渇、DBアクセス不能）
- BUG_MINOR: Cursorで自動修正すべきバグ（ロジックエラー、KeyError、データ不整合）
- SKIP: 再発しないノイズ・既知の警告

## CostGuard
- 環境変数: COST_DAILY_LIMIT_BUGWATCH=1.0 (USD)
- cost_guard.pyのget_costs()は流用不可（別バジェット管理）
- 独自カウンタをauto_bug_watcher/logs/cost_today.jsonで管理
- 超過時はGPT診断スキップ（SKIPとして処理）

## アクション仕様
### BUG_CRITICAL
- LINE push送信（松野 Ue3508b43b84991f5a68281da5bf4cf39）
- Notion AI作業キューDB登録（状態: review）
- pending_tasksへの保存なし（人間判断待ち）

### BUG_MINOR
- pending_tasks/に指示書保存（YYYYMMDD_HHMMSS_bugfix_{system}.md）
- 重複チェック: 同systemの未処理指示書が既存なら上書きしない
- Notion AI作業キューDB登録（状態: queued）

### SKIP
- Notion AI作業キューDB登録（状態: done）
- その他アクションなし

## 二重実行防止
- auto_bug_watcher/logs/watcher.lock
- 起動時にlockファイル確認、あれば即exit

## --dry-runオプション
- アクション実行せず、収集件数・診断結果・分岐先をコンソール出力のみ

## Notion AI作業キューDB スキーママッピング
- task_id: abw_{system}_{YYYYMMDD_HHMMSS}
- 受付元: auto_bug_watcher
- 種別: bug_critical / bug_minor / skip
- 優先度: 高（CRITICAL）/ 中（MINOR）/ 低（SKIP）
- 入力データ: {system, log_excerpt, gpt_diagnosis, gemini_diagnosis, agreement}
- 担当: cursor（MINOR） / jobz（CRITICAL） / -（SKIP）
- 状態: review（CRITICAL）/ queued（MINOR）/ done（SKIP）

## Notion API
- ヘッダー: Notion-Version: 2022-06-28
- POST https://api.notion.com/v1/pages
- config/.envのNOTION_API_KEYを使用
