import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()

# run_flag_updater.py 全内容確認
rfu = os.path.join(SES, "flag_auto_updater", "run_flag_updater.py")
with open(rfu, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

print(f"総行数: {len(lines)}")
for i, line in enumerate(lines, 1):
    print(f"L{i}: {line.rstrip()}")
