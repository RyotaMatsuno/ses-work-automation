import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()
mv3_dir = os.path.join(SES, "matching_v3")

# matching_v3.py の全内容確認
print("■ matching_v3.py 全内容")
with open(os.path.join(mv3_dir, "matching_v3.py"), encoding="utf-8", errors="replace") as f:
    content = f.read()
    lines = content.split("\n")

# main()関数全体
in_main = False
main_lines = []
for i, line in enumerate(lines, 1):
    if "def main(" in line:
        in_main = True
    if in_main:
        main_lines.append(f"  L{i}: {line}")
    if in_main and i > 50 and "def " in line and "def main" not in line:
        break

print("\n--- main()関数 ---")
for l in main_lines[:80]:
    print(l)

# flagauto_updaterのimportをチェック
print("\n--- import部分 ---")
for i, line in enumerate(lines[:50], 1):
    print(f"  L{i}: {line}")

# flag_auto_updaterが呼ばれている箇所
print("\n--- flag_auto_updater参照箇所 ---")
for i, line in enumerate(lines, 1):
    if "flag_auto" in line.lower() or "run_flag" in line.lower() or "updater" in line.lower():
        print(f"  L{i}: {line}")
