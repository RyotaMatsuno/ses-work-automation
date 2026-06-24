# task_auto_runner TASKS.md
最終更新: 2026-06-12

## Phase 1: 基盤
- [ ] task_auto_runner/CLAUDE.md 作成
- [ ] 新規ディレクトリ作成: running_tasks/ done_tasks/ blocked_tasks/
- [ ] task_auto_runner/logs/ 作成

## Phase 2: claude_invoker.py
- [ ] invoke_claude_code(instruction_path, budget_usd=5, timeout=1500) 関数
- [ ] subprocess.run でCLI起動。--output-format json
- [ ] 戻り値: {exit_code, stdout, stderr, duration_sec, cost_usd}
- [ ] cost_usd は JSON出力の "total_cost_usd" フィールドから抽出
- [ ] タイムアウト時は exit_code=-1, stderr="TIMEOUT"

## Phase 3: gate_runner.py
- [ ] extract_target_file(instruction_text) 関数
  - 正規表現で「対象ディレクトリ:」「対象ファイル:」を抽出
  - ディレクトリの場合、git diff --name-only HEAD~1 で直近変更ファイル取得
  - 失敗時は対象ディレクトリ内の SPEC.md を返す
- [ ] run_gate_check(target_file) 関数
  - subprocess.run(['python', 'gate_checker/gate_check.py', '--phase', 'implementation', '--file', target_file])
  - 戻り値: {verdict: "OK"/"NG", judgment: "GO"/"NG"/"条件付きGO", reason}
- [ ] handle_ng(instruction_path, reason) 関数
  - ファイル名から試行回数(__tryN)を抽出
  - N>=2 なら blocked_tasks/ 移動
  - N<2 なら pending_tasks/ に __try{N+1} で再保存

## Phase 4: notifier.py
- [ ] daily_report.py の push_message() 関数をimport
- [ ] notify_success(filename, cost, duration)
- [ ] notify_retry(filename, try_num, reason)
- [ ] notify_blocked(filename, reason)
- [ ] notify_cost_guard(monthly)
- [ ] config/.env から LINE_CHANNEL_ACCESS_TOKEN と松野 user_id を読む

## Phase 5: runner.py（メインループ）
- [ ] sys.stdout.reconfigure(encoding='utf-8', errors='replace') 冒頭配置
- [ ] argparse: --dry-run オプション
- [ ] lock取得: logs/runner.lock にPID書き込み（生きていればexit）
- [ ] CostGuard チェック: get_costs() で monthly確認、$140超ならabort+LINE
- [ ] pending_tasks/*.md を更新日時の古い順にソート
- [ ] 各ファイルを順次:
  1. running_tasks/ に進行ログ書き込み
  2. claude_invoker.invoke_claude_code() 実行
  3. gate_runner.run_gate_check()
  4. 成功 → done_tasks/ 移動 + notify_success
  5. NG → gate_runner.handle_ng() → notify_retry or notify_blocked
- [ ] try/finally で lock 必ず解放
- [ ] 全体ログ: logs/runner_YYYYMMDD.log

## Phase 6: 起動バッチ
- [ ] task_auto_runner/run_auto_runner.bat
  ```
  @echo off
  cd /d "C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
  python task_auto_runner\runner.py >> task_auto_runner\logs\bat_run.log 2>&1
  ```

## Phase 7: Windowsタスクスケジューラ登録
- [ ] schtasks /create /tn "SES_TaskAutoRunner" /tr "<bat絶対パス>" /sc MINUTE /mo 5 /f

## Phase 8: 動作確認
- [ ] python task_auto_runner/runner.py --dry-run
  → pending_tasks/ スキャン結果が出力されること
- [ ] テスト用ダミー指示書を pending_tasks/ に置いて実走確認
- [ ] LINE通知が松野に届くこと
