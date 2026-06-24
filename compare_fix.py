import json
from collections import defaultdict

# 6/3の今日のログを時間別に確認（修正後の正常稼働）
current_log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log.jsonl"

hourly = defaultdict(float)
hourly_count = defaultdict(int)

with open(current_log, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
            ts = r.get("ts", "")
            hour = ts[:13]
            cost = float(r.get("cost_usd", 0) or 0)
            hourly[hour] += cost
            hourly_count[hour] += 1
        except:
            pass

print("=== 6/3 時間別コスト（修正後） ===")
total = 0
for h in sorted(hourly.keys()):
    if "2026-06-03" in h:
        print(f"  {h}: ${hourly[h]:.4f} ({hourly_count[h]}件)")
        total += hourly[h]
print(f"\n6/3合計: ${total:.4f}")

# 6/2との比較
archive_jun = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log_archive_2026-06.jsonl"
jun2_total = 0
jun2_count = 0
with open(archive_jun, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
            if r.get("ts", "").startswith("2026-06-02"):
                jun2_total += float(r.get("cost_usd", 0) or 0)
                jun2_count += 1
        except:
            pass
print(f"\n6/2（バグあり）: ${jun2_total:.4f} / {jun2_count}件")
print(f"6/3（修正後）: ${total:.4f} / {sum(hourly_count[h] for h in hourly_count if '2026-06-03' in h)}件")
print(f"削減率: {(1 - total / jun2_total) * 100:.1f}%")
