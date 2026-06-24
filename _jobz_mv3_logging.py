import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()
mv3_dir = os.path.join(SES, "matching_v3")

# matching_v3.py の _setup_logging と logger 設定を確認
print("■ matching_v3.py の logging 設定箇所")
with open(os.path.join(mv3_dir, "matching_v3.py"), encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    if any(
        kw in line
        for kw in ["_setup_logging", "basicConfig", "FileHandler", "getLogger", "log_path", "log_dir", "logger ="]
    ):
        print(f"  L{i}: {line.rstrip()}")

# _setup_logging 関数の全内容
print("\n■ _setup_logging 全内容")
in_func = False
for i, line in enumerate(lines, 1):
    if "def _setup_logging" in line:
        in_func = True
    if in_func:
        print(f"  L{i}: {line.rstrip()}")
    if in_func and i > 5 and line.strip().startswith("def ") and "_setup_logging" not in line:
        break

# _run_live の冒頭（_setup_logging呼び出し確認）
print("\n■ _run_live の冒頭")
in_func = False
count = 0
for i, line in enumerate(lines, 1):
    if "def _run_live" in line:
        in_func = True
    if in_func:
        print(f"  L{i}: {line.rstrip()}")
        count += 1
    if in_func and count > 20:
        break
