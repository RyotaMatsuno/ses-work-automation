import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
UTC = timezone.utc
now = datetime.now(JST)

cost_log = "usage_tracker/cost_log.jsonl"
records = []
with open(cost_log, encoding="utf-8", errors="replace") as f:
    for line in f:
        try:
            r = json.loads(line.strip())
            ts_str = r.get("ts", "")
            if not ts_str:
                continue
            ts_str2 = ts_str.replace("Z", "+00:00")
            ts = datetime.fromisoformat(ts_str2)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            records.append(
                {
                    "ts": ts,
                    "cost": float(r.get("cost_usd", 0) or 0),
                    "model": r.get("model", ""),
                    "task": r.get("task", ""),
                }
            )
        except:
            pass

now_utc = now.astimezone(UTC)
month_start = now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
hour_start = now_utc - timedelta(hours=1)

monthly = sum(r["cost"] for r in records if r["ts"] >= month_start)
daily = sum(r["cost"] for r in records if r["ts"] >= today_start)
hourly = sum(r["cost"] for r in records if r["ts"] >= hour_start)

print("=" * 60)
print("【1】cost_log.jsonl 実コスト集計")
print("=" * 60)
print(f"  総レコード数: {len(records)}件")
print()
print(f"  今月累計 : ${monthly:.4f}  (上限$140  → 残り${140 - monthly:.2f})")
print(f"  今日累計 : ${daily:.4f}   (上限$8    → 残り${8 - daily:.2f})")
print(f"  直近1時間: ${hourly:.4f}")
print()

# 日別（直近14日）
by_day = {}
for r in records:
    day = r["ts"].astimezone(JST).strftime("%Y-%m-%d")
    by_day[day] = by_day.get(day, 0) + r["cost"]
print("  日別コスト（直近14日）:")
max_cost = max(by_day.values()) if by_day else 1
for day in sorted(by_day.keys())[-14:]:
    c = by_day[day]
    bar = "█" * max(1, int(c / max_cost * 30))
    flag = " ⚠️危険！" if c > 8 else (" 🟡注意" if c > 4 else "")
    print(f"    {day}: ${c:.4f} {bar}{flag}")

# モデル別
by_model = {}
for r in records:
    m = r["model"] or "unknown"
    if m not in by_model:
        by_model[m] = {"cost": 0, "count": 0}
    by_model[m]["cost"] += r["cost"]
    by_model[m]["count"] += 1
print()
print("  モデル別コスト（全期間）:")
for m, v in sorted(by_model.items(), key=lambda x: -x[1]["cost"]):
    print(f"    {m}: ${v['cost']:.4f} ({v['count']}件 avg=${v['cost'] / v['count']:.5f})")
