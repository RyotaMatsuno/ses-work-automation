import json
from collections import defaultdict

archive = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log_archive_2026-06.jsonl"
daily = defaultdict(float)
total = 0.0

with open(archive, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
            d = r.get("date", "")
            cost = float(r.get("total_cost_usd", 0) or 0)
            daily[d] += cost
            total += cost
        except:
            pass

print("=== 日別コスト（直近） ===")
for k in sorted(daily.keys())[-10:]:
    print(f"  {k}: ${daily[k]:.4f}")
print(f"\n月合計: ${total:.4f}")
