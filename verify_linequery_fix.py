import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

lw = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"

# 1. 構文チェック
r = subprocess.run(
    ["python", "-m", "py_compile", "line_query.py"], cwd=lw, capture_output=True, text=True, encoding="utf-8"
)
print(f"syntax check: {'OK' if r.returncode == 0 else 'ERROR'}")
if r.stderr:
    print(r.stderr)

# 2. 修正箇所を確認
with open(os.path.join(lw, "line_query.py"), encoding="utf-8") as f:
    lines = f.readlines()

print(f"\nTotal lines: {len(lines)}")

# BUG-3: _match_station
print("\n=== BUG-3: _match_station ===")
for i, line in enumerate(lines, 1):
    if "_match_station" in line or ("return False" in line and i > 160 and i < 185):
        print(f"L{i}: {line.rstrip()}")

# BUG-2: _gross_threshold
print("\n=== BUG-2: _gross_threshold ===")
for i, line in enumerate(lines, 1):
    if "GROSS_THRESHOLDS" in line or "_gross_threshold" in line:
        print(f"L{i}: {line.rstrip()}")

# BUG-1: _limit_reply
print("\n=== BUG-1: _limit_reply ===")
in_func = False
for i, line in enumerate(lines, 1):
    if "def _limit_reply" in line:
        in_func = True
    if in_func:
        print(f"L{i}: {line.rstrip()}")
        if in_func and i > 5 and line.strip().startswith("def ") and "_limit_reply" not in line:
            break

# BUG-4: engineer_query filter
print("\n=== BUG-4: engineer_query filter ===")
for i, line in enumerate(lines, 1):
    if "VAL_ADJUSTING" in line or "VAL_RECRUITING" in line:
        print(f"L{i}: {line.rstrip()}")
