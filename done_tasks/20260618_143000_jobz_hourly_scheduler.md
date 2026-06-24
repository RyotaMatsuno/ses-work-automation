【Cursor作業指示】
タスクID: jobz_hourly_scheduler
作成日時: 2026-06-18 14:30
作成者: ジョブズ
壁打ち根拠: auto_coder/wall_hitting_bugs_round8.txt (GPT-5.4合意)

# 背景・経緯
- 2026-06-17 19:53以降、mail_pipelineのWindows Task Schedulerが3重トラップで頻繁にスキップ:
  1. 手動Run→次回トリガをスキップ
  2. Set-ScheduledTask更新→次回トリガをスキップ
  3. PCスリープ→トリガ喪失
- 直接 wd_mail_pipeline.bat 実行は正常完走実証済み (12:37-12:41で139件処理)
- mail_pipeline.py本体・matching_v3・freee・LINE bridge・AI作業キューはすべて健全
- A1-α (matching_v2切り離し) も適用済みで効いている
- 結論: 「起動の親」だけWindows Task Schedulerを捨ててjobz-command内蔵にする

# 目的
jobz-command (localhost:8765) に毎時00分発火機能を追加し、Windows Task Schedulerへの依存を完全に廃止する。

# 対象ディレクトリ
ses_work/local_server/

# 設計 (SPEC)

## 新規ファイル
ses_work/local_server/scheduler.py

## 既存ファイルへの追加
ses_work/local_server/command_server.py
  - 起動時にscheduler.pyのスレッドを起動
  - 新規エンドポイント `/jobs/mail_pipeline/run` `/jobs/mail_pipeline/status` `/jobs/mail_pipeline/history` を追加

## scheduler.py の責務
1. 毎時00分にmail_pipelineを実行 (許容ズレ±60秒)
2. catch-up処理:
   - プロセス起動時、スリープ復帰後の最初のtick時、過去の未実行スロットを最大3個まで補填実行
   - 無限catch-upは禁止
3. 二重起動防止:
   - lock file: ses_work/job_state/mail_pipeline_hourly.lock
   - lock取得失敗時は当該スロットをskip
4. 永続state: ses_work/job_state/mail_pipeline_hourly.json
   - last_scheduled_slot (ISO形式)
   - last_started_at
   - last_finished_at
   - last_exit_code
   - last_success_at
   - last_skipped_slot (catch-up上限超過時)
5. ログ: ses_work/logs/mail_pipeline_hourly/YYYY-MM-DD.log
   - 1実行ごとに start/end/exit_code/scheduled_slot を記録
6. 実行コマンド: cmd /c "<ses_work_dir>\wd_mail_pipeline.bat" (既存と同じ経路、weekday_guard.py通過)
   - working directory: ses_work
   - stdout/stderr はログファイルへ
7. 起動はcommand_server.py内のbackgroundスレッドとして同居 (別プロセス化しない)

## API仕様

### POST /jobs/mail_pipeline/run
手動実行。response: {"ok": True, "job_id": "..."}
lock取得済みならresponse: {"ok": False, "reason": "already_running"}

### GET /jobs/mail_pipeline/status
response: {
  "running": bool,
  "last_started_at": "...",
  "last_finished_at": "...",
  "last_exit_code": int|null,
  "last_success_at": "...",
  "next_due_at": "...",
  "last_scheduled_slot": "..."
}

### GET /jobs/mail_pipeline/history?limit=20
最近の実行履歴(最大100件)を返す。response: [{...}, {...}, ...]

## 認証
既存と同じ X-Auth-Token: jobz-terra-2026

## 異常系
- exit_code != 0: 失敗記録のみ。次の毎時実行は通常継続
- mail_pipeline.py自体のretry/network再試行はSPEC外 (mail_pipeline側責任)

## Windows Task Scheduler廃止手順 (実装完了後の運用切り替え)
- SES_MailPipeline: 既に Disabled
- SES_MailPipeline_R7: 実装完了後にDisable(削除はしない、切り戻し用)

# タスクリスト (TASKS)

1. [ ] scheduler.pyの新規作成
   - hourly scheduler loop
   - catch-up logic (上限3スロット)
   - lock file制御
   - state永続化 (json)
   - 日次ログローテーション

2. [ ] command_server.pyに統合
   - 起動時にscheduler threadを開始
   - 新規エンドポイント3つを追加

3. [ ] job_stateディレクトリ・logsディレクトリの作成 (mkdir)

4. [ ] 単体テスト:
   - 手動runで実行成功
   - 実行中の2回目runが二重起動防止される
   - stateを過去時刻に戻すとcatch-upが1回動く
   - status/historyが正しく返る

5. [ ] 既存wd_mail_pipeline.batとの結合テスト:
   - schedulerから起動して pipeline.log にSTART/DONEが記録される
   - exit_code 0で正常完了
   - 所要時間が直接実行と同等(5分以内)

6. [ ] Windows起動時の自動起動確認 (既存 start_server.bat 経由)
   - PC再起動後、command_serverが起動 → scheduler thread起動 → 次の毎時tick発火
   - 手順書を local_server/README.md に追記

7. [ ] 運用切替:
   - SES_MailPipeline_R7 を schtasks /Change /Disable
   - 24時間観測 → 問題なければCron依存ゼロ運用確定

# 受け入れ条件
- 毎時00分に自動実行され、pipeline.log にSTART/DONEが記録される
- 手動APIで即時実行できる
- 実行中の二重起動が防止される
- PC起動後・スリープ復帰後にcatch-upが動く (上限3スロット)
- jobz-command停止時はscheduler thread も停止 (孤児プロセスなし)
- Windows Task Schedulerに一切依存しない

# 注意事項
- jobz-command起動時に常駐するため、PCが起動中は常に動く
- スリープ中はscheduler自身も停止 → 復帰時のcatch-up処理が肝
- 27分超のタイムアウト問題はmail_pipeline側で考慮済み (実績5分以内)
- 既存 cost_log.jsonl / state.sqlite3 への影響なし

# ゲートチェック
実装完了後、以下を実行:
  python gate_checker/gate_check.py --phase implementation --file local_server/scheduler.py
  python gate_checker/gate_check.py --phase implementation --file local_server/command_server.py
GO判定後にCron切替を実施。

# 質問・調整事項がある場合
Claude.aiチャットに貼り付けて確認。
