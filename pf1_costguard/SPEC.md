> ⚠ **2026-06-16でフリーズ。最新は `cost_guard_v2/` を参照**
>
> このディレクトリは6/5時点の設計で凍結されています。装置1〜3 + DAILY_CALL_LIMIT を含む最新仕様は `ses_work/cost_guard_v2/SPEC.md` v2.2 を参照してください。

---

# SPEC.md - Phase1: cost_guard 全面改修

## 背景（監査結果要約）
- LLMを叩く経路が8系統あるが、現cost_guard.pyが停止できるのはSES_MailPipeline + 無効化済SES_MatchingAndNotify(no-op)の実質1系統のみ
- get_costs()はscript絞りなしの合算だが、disable_tasks()の対象が不十分
- アクティブな消費者: SES_MailPipeline / SES_MatchingV3 / jobz_importer / SES_Outlook_9h / SES_Outlook_13h / SES_Outlook_18h / Cloud Run(line-webhook)
- 上限: ソフト$6/日(警告) / ハード$8/日(停止) / 月次$140(停止)

## 変更対象ファイル
- `../cost_guard.py`（上書き全面改修）
- `setup_schedule.py`（新規作成・実行: CostGuardを5分毎に変更するスクリプト）

## cost_guard.py の新しい仕様

### 定数
```
SOFT_DAILY_LIMIT  = 6.0   # 警告（タスクは止めない）
HARD_DAILY_LIMIT  = 8.0   # 全停止 + LINE通知
MONTHLY_LIMIT     = 140.0 # 全停止 + LINE通知
COST_LOG = Path(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log.jsonl')
LINE_USER_ID = 'Ue3508b43b84991f5a68281da5bf4cf39'
```

### ACTIVE_TASKS (停止・再起動対象)
```python
ACTIVE_TASKS = [
    'SES_MailPipeline',
    'SES_MatchingV3',
    'jobz_importer',
    'SES_Outlook_9h',
    'SES_Outlook_13h',
    'SES_Outlook_18h',
]
```

### get_costs() → (hourly: float, daily: float, monthly: float)
- cost_log.jsonlを全行読み込み（script絞りなし）
- hourly: 過去1時間の合算
- daily: JST 00:00以降の合算
- monthly: 今月1日以降の合算
- エラー時は (0,0,0) を返す

### disable_tasks() / enable_tasks()
- schtasks /Change /TN <task_name> /DISABLE  (または /ENABLE)
- Cloud Runキル: subprocess で gcloud run services update line-webhook --region asia-northeast1 --update-env-vars LLM_KILL=1
- Cloud Run再起動: LLM_KILL=0
- gcloud失敗はログ出力のみ（致命的エラー扱いしない）

### STATE_FILE
`ses_work/cost_guard_state.json`
```json
{"stopped_today": false, "stopped_monthly": false, "soft_alerted_today": false, "last_date": "2026-06-05", "last_month": "2026-06"}
```
- 1日の日付が変わったら stopped_today / soft_alerted_today をリセット（月が変わったら stopped_monthly もリセット）
- 既にその種別の通知/停止を済ませていたら重複実行しない

### main() ロジック
1. load_state()
2. check/reset date
3. get_costs() → hourly, daily, monthly
4. 判定:
   - monthly >= MONTHLY_LIMIT かつ stopped_monthly=False → disable_tasks() + LINE送信 + state.stopped_monthly=True
   - daily >= HARD_DAILY_LIMIT かつ stopped_today=False → disable_tasks() + LINE送信 + state.stopped_today=True
   - daily >= SOFT_DAILY_LIMIT かつ soft_alerted_today=False → LINE警告のみ + state.soft_alerted_today=True
   - daily < SOFT_DAILY_LIMIT かつ stopped_today=True → enable_tasks() + LINE「復旧」 + state.stopped_today=False
5. save_state()
6. print ログ出力

### LINE送信
push API: POST https://api.line.me/v2/bot/message/push
Authorization: Bearer {LINE_CHANNEL_ACCESS_TOKEN env}
エラー時はprint出力のみ

## setup_schedule.py の仕様
- PowerShellコマンドでSES_CostGuardのRepetitionInterval を PT5M（5分毎）に変更
- コマンド: `schtasks /Change /TN SES_CostGuard /RI 5` (または xml経由)
- 変更後にSES_CostGuardを即時実行: `schtasks /Run /TN SES_CostGuard`
- 成功/失敗をprint出力
