import datetime
import json
import urllib.request

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_API_KEY")
PROJECT_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"

# 2日以内の案件数を取得
two_days_ago = (datetime.datetime.now() - datetime.timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S+09:00")

payload = {"page_size": 100, "filter": {"property": "登録日時", "date": {"after": two_days_ago}}}

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

# コストシミュレーション
cost_per_call = 0.0094
active_projects = count

print("\n=== コストシミュレーション ===")
print(f"前提: 2日以内案件={active_projects}件, 1回のAI判定=${cost_per_call}")
print()

# 新着人材のみ（1日30人）
new_only_calls = 30 * active_projects
new_only_daily = new_only_calls * cost_per_call
print("【新着人材のみ】")
print(f"  30人 × {active_projects}件 = {new_only_calls}回/日 → ${new_only_daily:.2f}/日 → 月${new_only_daily * 30:.0f}")
print()

# 既存人員1日1回追加
existing = 126
batch1_calls = existing * active_projects
batch1_daily = batch1_calls * cost_per_call
total1_daily = new_only_daily + batch1_daily
print("【新着+既存1日1回】")
print(f"  既存{existing}人 × {active_projects}件 = {batch1_calls}回/日 → ${batch1_daily:.2f}/日")
print(f"  合計: ${total1_daily:.2f}/日 → 月${total1_daily * 30:.0f}")
