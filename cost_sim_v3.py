import datetime
import json
import urllib.request

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_API_KEY")
PROJECT_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"

# created_timeフィルターで2日以内を取得
two_days_ago = (
    datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))) - datetime.timedelta(days=2)
).strftime("%Y-%m-%dT%H:%M:%S+09:00")

payload = {"page_size": 100, "filter": {"timestamp": "created_time", "created_time": {"after": two_days_ago}}}

count = 0
cursor = None
while True:
    if cursor:
        payload["start_cursor"] = cursor
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"https://api.notion.com/v1/databases/{PROJECT_DB}/query",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        res = json.loads(r.read())
    count += len(res.get("results", []))
    if not res.get("has_more"):
        break
    cursor = res.get("next_cursor")

print(f"2日以内の案件数: {count}件")

cost_per_call = 0.0094
active = count
existing = 126

print("\n=== コストシミュレーション ===")

new_daily = 30 * active * cost_per_call
print(f"【新着人材のみ】 30人×{active}件 → ${new_daily:.2f}/日 → 月${new_daily * 30:.0f}")

batch_daily = existing * active * cost_per_call
total_daily = new_daily + batch_daily
print(f"【+既存1日1回】 126人×{active}件 → +${batch_daily:.2f}/日 → 合計月${total_daily * 30:.0f}")
