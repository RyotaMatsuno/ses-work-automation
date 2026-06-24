# -*- coding: utf-8 -*-
# 今日のコスト推移を時系列で確認してオートチャージ理由を特定
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

JST = timezone(timedelta(hours=9))
cost_log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log.jsonl")

# 過去7日間の日別・スクリプト別コスト
daily = defaultdict(lambda: defaultdict(float))
daily_total = defaultdict(float)
daily_calls = defaultdict(int)

with cost_log.open(encoding="utf-8", errors="replace") as f:
    for line in f:
        try:
            e = json.loads(line)
            ts = e.get("ts", "")
            day = ts[:10]
            script = e.get("script", "?")
            cost = e.get("cost_usd", 0)
            daily[day][script] += cost
            daily_total[day] += cost
            daily_calls[day] += 1
        except:
            pass

print("=== 過去7日間の日別コスト ===")
for day in sorted(daily_total.keys())[-7:]:
    print(f"\n{day}: ${daily_total[day]:.4f} ({daily_calls[day]}コール)")
    for script, cost in sorted(daily[day].items(), key=lambda x: -x[1])[:5]:
        print(f"    {script}: ${cost:.4f}")

# Anthropicの課金は日次なのか月次なのか確認
print("\n\n=== 月次累計（今月） ===")
this_month = datetime.now(JST).strftime("%Y-%m")
month_total = sum(v for k, v in daily_total.items() if k.startswith(this_month))
print(f"  6月累計: ${month_total:.4f}")

# 日次$8上限を超えた日があるか
print("\n=== 日次$8上限超過チェック ===")
for day in sorted(daily_total.keys()):
    if daily_total[day] > 8:
        print(f"  ⚠️ {day}: ${daily_total[day]:.4f} (上限$8超過!)")
    elif daily_total[day] > 5:
        print(f"  {day}: ${daily_total[day]:.4f} (要注意)")
