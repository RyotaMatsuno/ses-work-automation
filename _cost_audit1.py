import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
now = datetime.now(JST)

# ===== 1. cost_log.jsonl の全件集計 =====
print("=" * 60)
print("【1】cost_log.jsonl 実コスト集計")
print("=" * 60)

cost_log = "usage_tracker/cost_log.jsonl"
if not os.path.exists(cost_log):
    print("  ❌ ファイルなし")
else:
    records = []
    with open(cost_log, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                r = json.loads(line.strip())
                ts_str = r.get("ts", "")
                if ts_str:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
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

    # 日別集計（直近30日）
    by_day = {}
    for r in records:
        day = r["ts"].astimezone(JST).strftime("%Y-%m-%d")
        by_day[day] = by_day.get(day, 0) + r["cost"]

    print(f"  総レコード数: {len(records)}件")
    print("\n  日別コスト（直近14日）:")
    for day in sorted(by_day.keys())[-14:]:
        bar = "█" * int(by_day[day] * 20)
        flag = " ⚠️ 危険" if by_day[day] > 8 else (" ⚡" if by_day[day] > 4 else "")
        print(f"    {day}: ${by_day[day]:.4f} {bar}{flag}")

    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly = sum(r["cost"] for r in records if r["ts"] >= month_start.astimezone(timezone.utc))
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    daily = sum(r["cost"] for r in records if r["ts"] >= today_start.astimezone(timezone.utc))

    print(f"\n  今月累計: ${monthly:.4f}")
    print(f"  今日累計: ${daily:.4f}")
    print(f"  月次上限: $140.00 → 残り: ${140 - monthly:.2f}")
    print(f"  日次上限: $8.00 → 残り: ${8 - daily:.2f}")

    # モデル別集計
    by_model = {}
    for r in records[-1000:]:  # 直近1000件
        m = r["model"] or "unknown"
        by_model[m] = by_model.get(m, {"cost": 0, "count": 0})
        by_model[m]["cost"] += r["cost"]
        by_model[m]["count"] += 1
    print("\n  モデル別（直近1000件）:")
    for m, v in sorted(by_model.items(), key=lambda x: -x[1]["cost"]):
        print(f"    {m}: ${v['cost']:.4f} ({v['count']}件)")
