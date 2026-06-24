# jobz-command ローカルサーバー

## 起動

```bat
cd /d "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\local_server"
python command_server.py
```

または `start_server.bat`（スタートアップ登録済み）。

## ヘルスチェック

```bat
curl.exe -s -H "X-Auth-Token: jobz-terra-2026" http://127.0.0.1:8765/health
```

## mail_pipeline スケジューラ（2026-06-19〜 Task J）

**本番実行は Windows Task Scheduler（`SES_MailPipeline`）に一本化済み。**

`scheduler.py` は廃止（直接実行・`POST /jobs/mail_pipeline/run` は 410）。`command_server` 起動時もスケジューラスレッドは起動しない。

二重起動防止は `mail_pipeline.py` のファイルロック（`%LOCALAPPDATA%\ses_work_state\pipeline.lock`）で担保。

### Task Scheduler 確認

```bat
schtasks /Query /TN "SES_MailPipeline" /FO LIST
```

### 参照用 API（読み取りのみ）

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/jobs/mail_pipeline/status` | 最終実行状態（deprecated フラグ付き） |
| GET | `/jobs/mail_pipeline/history?limit=20` | 直近の実行履歴 |
| POST | `/jobs/mail_pipeline/run` | **廃止**（410 deprecated_use_task_scheduler） |

認証: `X-Auth-Token: jobz-terra-2026`

### 状態ファイル（レガシー参照用）

- `ses_work/job_state/mail_pipeline_hourly.json` — 過去の scheduler.py 実行履歴
- `ses_work/logs/mail_pipeline_hourly/` — 過去ログ

### PC再起動後の確認

1. `schtasks /Query /TN "SES_MailPipeline"` で Ready であること
2. 毎時00分前後に `mail_pipeline/pipeline.log` に処理が記録されること
3. 手動二重起動時は「別プロセスが実行中 - スキップ」で exit 0 になること
