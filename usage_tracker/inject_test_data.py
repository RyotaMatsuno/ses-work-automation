import json
from datetime import datetime, timedelta, timezone

# 昨日の日付でテストデータを作成
yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")

records = [
    {
        "ts": yesterday,
        "script": "matching_v2",
        "model": "claude-haiku-4-5-20251001",
        "input_tokens": 5000,
        "output_tokens": 800,
        "cached_tokens": 3000,
        "cost_usd": 0.00072,
    },
    {
        "ts": yesterday,
        "script": "matching_v2",
        "model": "claude-haiku-4-5-20251001",
        "input_tokens": 4200,
        "output_tokens": 650,
        "cached_tokens": 2800,
        "cost_usd": 0.00061,
    },
    {
        "ts": yesterday,
        "script": "mail_pipeline",
        "model": "claude-haiku-4-5-20251001",
        "input_tokens": 1200,
        "output_tokens": 300,
        "cached_tokens": 0,
        "cost_usd": 0.00217,
    },
]

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log.jsonl"
with open(log_path, "w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"Written {len(records)} test records to cost_log.jsonl", flush=True)
