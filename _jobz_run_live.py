import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()
mv3 = os.path.join(SES, "matching_v3", "matching_v3.py")

with open(mv3, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

# _run_live の全体を確認（案件取得〜マッチング部分）
print("■ _run_live 全内容")
in_func = False
count = 0
for i, line in enumerate(lines, 1):
    if "def _run_live" in line:
        in_func = True
    if in_func:
        print(f"  L{i}: {line.rstrip()}")
        count += 1
    if in_func and count > 5 and line.strip().startswith("def ") and "_run_live" not in line:
        break
