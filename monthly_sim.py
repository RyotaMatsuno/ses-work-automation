import json
from collections import defaultdict

# 5月アーカイブ（正常稼働日）
archive_may = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log_archive_2026-05.jsonl"
archive_jun = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log_archive_2026-06.jsonl"
current_log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log.jsonl"


def parse_log(path, daily):
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    ts = r.get("ts", "")
                    d = ts[:10]
                    cost = float(r.get("cost_usd", 0) or 0)
                    daily[d] += cost
                except:
                    pass
    except FileNotFoundError:
        pass


daily = defaultdict(float)
parse_log(archive_may, daily)
parse_log(archive_jun, daily)
parse_log(current_log, daily)

print("=== 全日別コスト ===")
for k in sorted(daily.keys()):
    flag = " ← 異常日" if daily[k] > 10 else ""
    print(f"  {k}: ${daily[k]:.3f}{flag}")

# 異常日除外の平均
normal_days = {k: v for k, v in daily.items() if v < 10 and v > 0}
if normal_days:
    avg = sum(normal_days.values()) / len(normal_days)
    print(f"\n正常稼働日の平均: ${avg:.3f}/日 ({len(normal_days)}日分)")
    print(f"月次推計（30日）: ${avg * 30:.2f}")
