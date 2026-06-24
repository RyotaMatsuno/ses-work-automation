import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()

# 修正後の gate_check.py 該当箇所を読む
print("■ gate_check.py resolve_human_review + run_gate_check 該当箇所")
gc_py = os.path.join(SES, "gate_checker", "gate_check.py")
with open(gc_py, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

# resolve_human_review 関数
in_func = False
for i, line in enumerate(lines, 1):
    if "def resolve_human_review" in line:
        in_func = True
    if in_func:
        print(f"  L{i}: {line.rstrip()}")
    if in_func and i > 5 and line.strip().startswith("def "):
        break

# run_gate_check 内の呼び出し箇所
print("\n  --- run_gate_check 内 human_review 呼び出し箇所 ---")
for i, line in enumerate(lines, 1):
    if "human_review" in line or "resolve_human_review" in line:
        print(f"  L{i}: {line.rstrip()}")

# テストファイル
print("\n■ test_human_review_override.py 全内容")
test_path = os.path.join(SES, "gate_checker", "tests", "test_human_review_override.py")
if os.path.exists(test_path):
    with open(test_path, encoding="utf-8", errors="replace") as f:
        print(f.read())
else:
    # tests/ 直下を探す
    tests_dir = os.path.join(SES, "gate_checker", "tests")
    if os.path.isdir(tests_dir):
        for fn in os.listdir(tests_dir):
            print(f"  {fn}")
    else:
        print("  tests/ 未存在")
