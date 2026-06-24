import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
today = date.today().strftime("%Y%m%d")

mv3_log = SES / "matching_v3" / "logs" / f"matching_v3_{today}.log"
fu_log = SES / "flag_auto_updater" / "logs" / f"flag_updater_{today}.log"

print(f"■ matching_v3_{today}.log: {mv3_log.stat().st_size if mv3_log.exists() else 'MISSING'}b")
if mv3_log.exists() and mv3_log.stat().st_size > 0:
    with open(mv3_log, encoding="utf-8", errors="replace") as f:
        for l in f.readlines():
            print("  " + l.rstrip())

print(f"\n■ flag_updater_{today}.log: {fu_log.stat().st_size if fu_log.exists() else 'MISSING'}b")
if fu_log.exists() and fu_log.stat().st_size > 0:
    with open(fu_log, encoding="utf-8", errors="replace") as f:
        for l in f.readlines()[-15:]:
            print("  " + l.rstrip())

# 修正後のコード確認
print("\n■ 修正後 _setup_logging 確認")
rfu = SES / "flag_auto_updater" / "run_flag_updater.py"
with open(rfu, encoding="utf-8") as f:
    content = f.read()
in_func = False
for i, line in enumerate(content.split("\n"), 1):
    if "def _setup_logging" in line:
        in_func = True
    if in_func:
        print(f"  L{i}: {line.rstrip()}")
    if in_func and i > 5 and line.strip().startswith("def ") and "_setup_logging" not in line:
        break
