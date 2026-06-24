# 【Cursor作業指示】Task O: nightly_jobz Phase 1 (最小構成)

（元仕様は pending_tasks にあったファイルと同一）

---

## 完了メモ（2026-06-19）

- `nightly_jobz/` 新規作成（config, notion_queue, task_processor, nightly_jobz.py）
- lock: `%LOCALAPPDATA%/ses_work_state/nightly_jobz.lock`
- Notionキュー取得（queued/running）+ investigation/spec_design 処理
- stub: draft_intent/draft_proposal/matching → blocked
- ブリーフィング: `logs/briefing_YYYYMMDD.json`
- `config/.env`: `COST_GUARD_NIGHTLY_USD=2.0`
- DRY_RUN=1 実実行成功（7件キュー取得・ブリーフィング生成）
- pytest 5件全パス

### 実行方法

```powershell
cd ses_work
$env:NIGHTLY_DRY_RUN="1"
python -m nightly_jobz.nightly_jobz
```

### スケジューラ登録例

```powershell
schtasks /Create /TN "SES_NightlyJobz" /TR "python -m nightly_jobz.nightly_jobz" /SC DAILY /ST 23:55 /F
```
