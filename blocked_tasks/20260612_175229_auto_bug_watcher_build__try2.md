【Cursor作業指示】auto_bug_watcher新規構築
対象ディレクトリ: ses_work/auto_bug_watcher/
参照ファイル: auto_bug_watcher/SPEC.md / auto_bug_watcher/TASKS.md / auto_bug_watcher/CLAUDE.md
完了条件: python auto_bug_watcher/watcher.py --dry-run が実行されログ収集→2AI診断→アクション分岐まで動作すること

━━━ ゲートチェック実行 ━━━
作業開始前に必ず以下を実行:
python gate_checker/gate_check.py --phase requirements --file auto_bug_watcher/SPEC.md
→ GO判定後に実装開始すること

━━━ TASKS ━━━

【Phase 1】auto_bug_watcher/CLAUDE.md を読んで作業方針を確認

【Phase 2】collectors/log_collector.py を実装
- 監視対象: mail_pipeline/logs, matching_v3/logs, freee/logs,
            mail_attachment_importer/logs, gate_checker/logs, line_webhook/logs
- 直近24時間のファイルから"ERROR"/"CRITICAL"/"Exception"/"Traceback"を含む行を抽出
- 正常パターン除外: "No new emails", "weekday_guard skip", "No match found"
- 戻り値: List[dict] = [{system, log_excerpt, timestamp}]
- ファイルが存在しない場合は空リストを返す（エラーにしない）

【Phase 3】collectors/scheduler_collector.py を実装
- schtasks /query /fo LIST /v を実行
- 以下タスクの最終実行結果が0以外のものを収集:
  SES_MailPipeline / SES_MatchingV3 / line_bridge_worker_health
  jobz_importer / usage_tracker_daily / freee_monthly
- 戻り値: List[dict] = [{system, log_excerpt, timestamp}]
- schtasksが失敗した場合は空リストを返す

【Phase 4】classifier.py を実装
- sys.path.insert(0, str(Path(__file__).resolve().parent.parent)) でagreement_checker をimport
  from gate_checker.agreement_checker import run_dual_review, _load_env
- BUG_CRITICAL/BUG_MINOR/SKIPの分類プロンプト:
  システムプロンプト:
    あなたはSESビジネスの自動化システムのエラーを診断するAIです。
    以下のエラーログを分析し、次の3分類のいずれかで判定してください。
    BUG_CRITICAL: 即時人間確認が必要（auth失敗/APIキー無効/DBアクセス不能/データ損失リスク）
    BUG_MINOR: Cursorで自動修正可能なバグ（ロジックエラー/KeyError/データ不整合/パス問題）
    SKIP: 再発しないノイズ・既知の警告・一時的なエラー
    判定は必ず【判定: BUG_CRITICAL】【判定: BUG_MINOR】【判定: SKIP】の形式で出力すること。
  ユーザープロンプト: "システム: {system}\nログ: {log_excerpt}"
- agreement_checker.run_dual_review()を呼び出す際、verdictの代わりにBUG_CRITICAL/BUG_MINOR/SKIP用に
  parse_judgmentを拡張せず、レスポンステキストから直接分類を抽出する独自パーサーを使う
  （run_dual_reviewはGO/NG判定なので、テキストから分類を後解析する形で実装）
- CostGuardラップ: auto_bug_watcher/logs/cost_today.json で管理
  COST_DAILY_LIMIT_BUGWATCH環境変数（デフォルト1.0USD）超過でSKIPに分類
- 戻り値: List[dict] = [{system, classification, gpt_text, gemini_text, reason}]

【Phase 5】actions/cursor_task_writer.py を実装
- BUG_MINOR判定時のみpending_tasks/に指示書を保存
- ファイル名: YYYYMMDD_HHMMSS_bugfix_{system}.md
- 重複チェック: pending_tasks/内に同systemのbugfixファイルが存在したら上書きしない
- 指示書テンプレート:
  【Cursor作業指示】{system} バグ自動修正
  対象ディレクトリ: ses_work/{system}/
  エラー内容: {log_excerpt}
  対応方針: エラー内容を分析して修正してください
  完了条件: エラーが再発しないこと
  ゲートチェック: python gate_checker/gate_check.py --phase implementation --file {対象ファイル}

【Phase 6】actions/line_alerter.py を実装
- BUG_CRITICAL判定時にLINE push送信
- config/.envから LINE_CHANNEL_ACCESS_TOKEN を読む
- 送信先: Ue3508b43b84991f5a68281da5bf4cf39 (松野)
- メッセージ形式:
  🚨 [auto_bug_watcher] {system} BUG_CRITICAL
  {log_excerpt[:200]}
  → Notion AI作業キューに登録済み

【Phase 7】actions/notion_logger.py を実装
- 全分類をAI作業キューDB（37a450ff-37c0-819a-981b-c2e06ed282bb）に登録
- POST https://api.notion.com/v1/pages
- ヘッダー: Authorization: Bearer {NOTION_API_KEY}, Notion-Version: 2022-06-28
- プロパティマッピング (SPEC.mdのスキーマ参照):
  task_id: abw_{system}_{timestamp}
  受付元: auto_bug_watcher
  種別: bug_critical/bug_minor/skip
  優先度: 高/中/低
  担当: cursor(MINOR) / jobz(CRITICAL) / 空白(SKIP)
  状態: review(CRITICAL) / queued(MINOR) / done(SKIP)
  入力データ: log_excerpt + 診断テキストをJSONで

【Phase 8】watcher.py（メイン）を実装
- sys.stdout.reconfigure(encoding='utf-8", errors='replace') を冒頭に配置
- --dry-runオプション: argparse使用
- lockファイル: auto_bug_watcher/logs/watcher.lock（PIDを書き込む）
  起動時に存在チェック→あればPIDが生きているか確認→生きていればexit
- 実行ログ: auto_bug_watcher/logs/YYYYMMDD.log（logging.FileHandlerで出力）
- メインフロー:
  1. lock取得
  2. collectors全実行（log_collector + scheduler_collector）
  3. 収集件数をログ出力
  4. 件数0なら "No bugs detected" を出力してcleanly exit
  5. classifier.classify_all(issues)を実行
  6. actionsを分岐実行（dry_runならログ出力のみ）
  7. lock解放
- 全体をtry/finally: finallyでlock解放

【Phase 9】run_watcher.bat を作成
内容:
@echo off
cd /d "C:\Users\ma_py\OneDrive\\u30c7\u30b9\u30af\u30c8\u30c3\u30d7\ses_work"
python auto_bug_watcher\watcher.py >> auto_bug_watcher\logs\bat_run.log 2>&1

【Phase 10】タスクスケジューラ登録
以下コマンドを実行:
schtasks /create /tn "SES_AutoBugWatcher" /tr "C:\Users\ma_py\OneDrive\\u30c7\u30b9\u30af\u30c8\u30c3\u30d7\ses_work\auto_bug_watcher\run_watcher.bat" /sc DAILY /st 08:05 /f

【Phase 11】動作確認
cd C:\Users\ma_py\OneDrive\<Unicodeパス>\ses_work
python auto_bug_watcher/watcher.py --dry-run
→ 収集ログ件数・診断結果・アクション分岐がコンソールに出力されること
→ auto_bug_watcher/logs/YYYYMMDD.log が生成されること

━━━ ゲートチェック（完了後） ━━━
python gate_checker/gate_check.py --phase implementation --file auto_bug_watcher/watcher.py
→ GO後にジョブズに報告


## RETRY 1 REASON
target_file not found: 


## RETRY 2 REASON
target_file not found: 


## BLOCKED REASON
target_file not found: 
