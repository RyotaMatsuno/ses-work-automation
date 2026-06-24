tasks = """# auto_bug_watcher TASKS.md
最終更新: 2026-06-12

## 実装チェックリスト

### Phase 1: ディレクトリ・CLAUDE.md
- [x] ディレクトリ構成作成（ジョブズが実施済み）
- [ ] auto_bug_watcher/CLAUDE.md作成

### Phase 2: collectors
- [ ] collectors/log_collector.py
  - 監視対象パス（ses_work/配下）から直近24h・ERROR系行を抽出
  - 正常パターン除外: "No new emails", "weekday_guard skip", "No match found"
  - 戻り値: List[dict] {system, log_excerpt, timestamp}

- [ ] collectors/scheduler_collector.py
  - schtasks /query /fo LIST /v でexit code非0のタスクを検出
  - 対象: SES_MailPipeline / SES_MatchingV3 / line_bridge_worker_health
           jobz_importer / usage_tracker_daily / freee_monthly
  - 戻り値: List[dict] {system, log_excerpt, timestamp}

### Phase 3: classifier.py
- [ ] agreement_checker.py をimport（sys.pathにgate_checker親を追加）
- [ ] BUG_CRITICAL/BUG_MINOR/SKIPの3分類プロンプト設計
- [ ] ThreadPoolExecutorで並列実行
- [ ] agreement_checker.run_dual_review()で合意判定
- [ ] CostGuardラップ（独自 cost_today.json、$1.00/日上限）
- [ ] 超過時はSKIPとして処理

### Phase 4: actions/
- [ ] actions/cursor_task_writer.py
  - BUG_MINOR → pending_tasks/YYYYMMDD_HHMMSS_bugfix_{system}.md
  - 重複チェック（同systemの未処理ファイルがあれば上書きしない）

- [ ] actions/line_alerter.py
  - BUG_CRITICAL → LINE push
  - LINE_CHANNEL_ACCESS_TOKEN / user_id: Ue3508b43b84991f5a68281da5bf4cf39
  - config/.envから読み込み

- [ ] actions/notion_logger.py
  - 全件をAI作業キューDB（37a450ff-37c0-819a-981b-c2e06ed282bb）に登録
  - SPEC.mdのスキーママッピング通りに実装
  - Notion-Version: 2022-06-28 ヘッダー必須

### Phase 5: watcher.py（メイン）
- [ ] --dry-runオプション実装
- [ ] .lockファイルで二重実行防止
- [ ] 実行ログ: auto_bug_watcher/logs/YYYYMMDD.log
- [ ] 全体をtry/exceptで囲み、異常終了時もNotionに記録
- [ ] sys.stdout.reconfigure(encoding='utf-8', errors='replace') を冒頭に配置

### Phase 6: 起動バッチ・タスクスケジューラ登録
- [ ] auto_bug_watcher/run_watcher.bat作成
  - cd /d "C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work"
  - python auto_bug_watcher\\watcher.py
- [ ] weekday_guard.py経由でschtasks登録
  - タスク名: SES_AutoBugWatcher
  - トリガー: 毎日 08:05
  - コマンド: run_watcher.bat経由

### Phase 7: 動作確認
- [ ] python auto_bug_watcher/watcher.py --dry-run
  → 収集ログ件数・診断結果・アクション分岐がコンソールに出力されること
  → auto_bug_watcher/logs/にログファイルが生成されること
  → エラー終了しないこと（0件でもOK）
"""

with open("auto_bug_watcher/TASKS.md", "w", encoding="utf-8") as f:
    f.write(tasks)
print("TASKS.md written")
