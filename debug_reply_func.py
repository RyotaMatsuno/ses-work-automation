import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

ses = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
wh_path = os.path.join(ses, "line_webhook", "webhook_server.py")
with open(wh_path, encoding="utf-8") as f:
    lines = f.readlines()

# build_matching_result_reply L1183-1260 の全体
print("=== build_matching_result_reply L1183-1260 ===")
for i in range(1182, 1260):
    if i < len(lines):
        print(f"L{i + 1}: {lines[i]}", end="")

# get_active_projects L941-990
print("\n=== get_active_projects L941-990 ===")
for i in range(940, 990):
    if i < len(lines):
        print(f"L{i + 1}: {lines[i]}", end="")

# run_reverse_matching_full でのスコア0件除外ロジック
ml_path = os.path.join(ses, "line_webhook", "webhook_server.py")
print("\n=== run_reverse_matching_full L433-456 ===")
for i in range(432, 456):
    if i < len(lines):
        print(f"L{i + 1}: {lines[i]}", end="")
