import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

ses = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
ml_path = os.path.join(ses, "line_webhook", "matching_logic.py")
with open(ml_path, encoding="utf-8") as f:
    lines = f.readlines()

# L164以降全体
print("=== build_reverse_match_message_v2 L164-268 ===")
for i in range(163, len(lines)):
    print(f"L{i + 1}: {lines[i]}", end="")

# categorize_match も確認
print("\n=== categorize_match ===")
in_func = False
for i, line in enumerate(lines, 1):
    if "def categorize_match" in line:
        in_func = True
    if in_func:
        print(f"L{i}: {line}", end="")
        if i > 5 and line.strip().startswith("def ") and "categorize_match" not in line:
            break
