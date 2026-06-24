import json
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log.jsonl"
date_cost = defaultdict(float)
date_count = defaultdict(int)
tag_cost = defaultdict(float)
tag_count = defaultdict(int)

with open(path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            d = json.loads(line)
            ts = d.get("timestamp", "") or d.get("ts", "")
            cost = d.get("cost_usd", d.get("cost", 0)) or 0
            tag = d.get("tag") or d.get("source") or d.get("caller") or d.get("script") or "unknown"
            date_only = ts[:10]
            date_cost[date_only] += cost
            date_count[date_only] += 1
            tag_cost[tag] += cost
            tag_count[tag] += 1
        except Exception:
            pass

print("=== last 7 days ===")
for d in sorted(date_cost.keys())[-7:]:
    print(f"  {d}: ${date_cost[d]:.4f}  ({date_count[d]} calls)")

# Today's breakdown
import datetime

today_jst = (datetime.datetime.now() + datetime.timedelta(hours=9 if False else 0)).strftime("%Y-%m-%d")
# cost_log は UTC、ジョブズ環境はJST。今日のJST分相当をtodayとして抽出
today = datetime.datetime.now().strftime("%Y-%m-%d")
yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
print(f"\n=== TODAY ({today}) breakdown by tag ===")
today_cost = 0.0
today_tag_cost = defaultdict(float)
today_tag_count = defaultdict(int)
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            d = json.loads(line)
            ts = d.get("timestamp", "") or d.get("ts", "")
            cost = d.get("cost_usd", d.get("cost", 0)) or 0
            tag = d.get("tag") or d.get("source") or d.get("caller") or d.get("script") or "unknown"
            if ts.startswith(today):
                today_cost += cost
                today_tag_cost[tag] += cost
                today_tag_count[tag] += 1
        except Exception:
            pass
print(f"Total today: ${today_cost:.4f}")
for tag, c in sorted(today_tag_cost.items(), key=lambda x: -x[1]):
    print(f"  {tag}: ${c:.4f} ({today_tag_count[tag]} calls)")
