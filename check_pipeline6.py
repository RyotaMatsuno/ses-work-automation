import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ses_work = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
mp = ses_work / "mail_pipeline" / "mail_pipeline.py"

with open(mp, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

# FETCH_LIMIT / PROCESS_LIMIT 定義箇所
print("=== 定数定義 (先頭80行) ===")
for i, l in enumerate(lines[:80], 1):
    if any(k in l for k in ["LIMIT", "FETCH", "PROCESS", "cost", "COST", "budget", "BUDGET", "daily", "DAILY"]):
        print(f"L{i}: {l.rstrip()}")

# save_processed_id 関数の実装（L247〜270付近）
print("\n=== save_processed_id 関数 ===")
for i, l in enumerate(lines[245:275], 246):
    print(f"L{i}: {l.rstrip()}")

# fetch_recent_emails 関数の先頭（SINCE フィルタあるか）
fetch_start = None
for i, l in enumerate(lines):
    if "def fetch_recent_emails" in l:
        fetch_start = i
        break
if fetch_start:
    print(f"\n=== fetch_recent_emails (L{fetch_start + 1}〜+50) ===")
    for i, l in enumerate(lines[fetch_start : fetch_start + 50], fetch_start + 1):
        print(f"L{i}: {l.rstrip()}")
