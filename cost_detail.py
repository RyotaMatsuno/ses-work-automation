# -*- coding: utf-8 -*-
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

JST = timezone(timedelta(hours=9))
cost_log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log.jsonl")

today = datetime.now(JST).strftime("%Y-%m-%d")
this_month = datetime.now(JST).strftime("%Y-%m")

daily_by_hour = defaultdict(float)  # 時間帯別
daily_total = 0.0
monthly_total = 0.0
monthly_by_day = defaultdict(float)  # 日別
monthly_calls = 0
daily_calls = 0

with cost_log.open(encoding="utf-8", errors="replace") as f:
    for line in f:
        try:
            e = json.loads(line)
            ts = e.get("ts", "")
            cost = e.get("cost_usd", 0)
            if ts.startswith(this_month):
                monthly_total += cost
                monthly_calls += 1
                day = ts[:10]
                monthly_by_day[day] += cost
            if ts.startswith(today):
                daily_total += cost
                daily_calls += 1
                try:
                    hour = int(ts[11:13])
                    daily_by_hour[hour] += cost
                except Exception:
                    pass
        except Exception:
            pass

print("=" * 50)
print(f"【今日 {today}】")
print(f"  合計: ${daily_total:.4f}  ({daily_calls}コール)")
print()
print("  時間帯別:")
for h in sorted(daily_by_hour):
    bar = "█" * int(daily_by_hour[h] / 0.05)
    print(f"  {h:02d}時: ${daily_by_hour[h]:.4f}  {bar}")

print()
print("=" * 50)
print(f"【今月 {this_month}】")
print(f"  合計: ${monthly_total:.4f} / $140.00  ({monthly_calls}コール)")
print()
print("  日別:")
for d in sorted(monthly_by_day):
    bar = "█" * int(monthly_by_day[d] / 0.1)
    is_today = "← 今日" if d == today else ""
    print(f"  {d}: ${monthly_by_day[d]:.4f}  {bar} {is_today}")

print()
print(f"  月次残: ${140 - monthly_total:.2f}")
print(f"  日次残: ${8 - daily_total:.2f}")
