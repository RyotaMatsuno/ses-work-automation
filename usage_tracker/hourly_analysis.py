import json
from collections import defaultdict

archive = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log_archive_2026-06.jsonl"
# 時間帯別・スクリプト別の詳細
hourly = defaultdict(lambda: defaultdict(float))
hourly_count = defaultdict(lambda: defaultdict(int))

with open(archive, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
            ts = r.get("ts", "")
            hour = ts[:13] if ts else ""  # "2026-06-02T09"
            cost = float(r.get("cost_usd", 0) or 0)
            script = r.get("script", "unknown")
            hourly[hour][script] += cost
            hourly_count[hour][script] += 1
        except:
            pass

print("=== 時間帯別コスト（件数） ===")
for h in sorted(hourly.keys()):
    parts = []
    for s, c in sorted(hourly[h].items(), key=lambda x: -x[1]):
        cnt = hourly_count[h][s]
        parts.append(f"{s}:${c:.2f}({cnt}件)")
    print(f"  {h}: {', '.join(parts)}")
