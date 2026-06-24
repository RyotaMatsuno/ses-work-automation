import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

ses = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# matching_logic.py を確認
ml_path = os.path.join(ses, "line_webhook", "matching_logic.py")
if not os.path.exists(ml_path):
    # 探す
    for root, dirs, files in os.walk(ses):
        for f in files:
            if f == "matching_logic.py":
                print(os.path.join(root, f))
    ml_path = None
else:
    print(f"Found: {ml_path}")

if ml_path:
    with open(ml_path, encoding="utf-8") as f:
        lines = f.readlines()
    print(f"Lines: {len(lines)}")

    # build_reverse_match_message_v2 全体
    print("\n=== build_reverse_match_message_v2 ===")
    in_func = False
    for i, line in enumerate(lines, 1):
        if "def build_reverse_match_message_v2" in line:
            in_func = True
        if in_func:
            print(f"L{i}: {line}", end="")
            if i > 10 and line.strip().startswith("def ") and "build_reverse_match_message_v2" not in line:
                break
