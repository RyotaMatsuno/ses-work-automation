import json
from collections import defaultdict

archive = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log_archive_2026-06.jsonl"
daily = defaultdict(float)
script_cost = defaultdict(float)
total = 0.0

with open(archive, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
            ts = r.get("ts", "")
            d = ts[:10] if ts else ""
            cost = float(r.get("cost_usd", 0) or 0)
            script = r.get("script", "unknown")
            daily[d] += cost
            script_cost[script] += cost
            total += cost
        except:
            pass

print("=== 日別コスト ===")
for k in sorted(daily.keys()):
    print(f"  {k}: ${daily[k]:.4f}")

print("\n=== スクリプト別コスト（今月） ===")
for k, v in sorted(script_cost.items(), key=lambda x: -x[1]):
    print(f"  {k}: ${v:.4f}")

print(f"\n月合計: ${total:.4f}")
