
import os, subprocess, sys

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# outreach送信者名・FPメール確認
outreach_py = os.path.join(base, "outreach_system", "outreach.py")
with open(outreach_py, encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if any(k in line for k in ['from_name', 'from_addr', 'sender', 'fp_mail', 'FP', '送信者', '差出人']):
        print(f"{i+1}: {line}", end="")

print("\n--- collect_targets.py status ---")
# targets.csv の中身確認
csv_path = os.path.join(base, "outreach_system", "targets.csv")
if os.path.exists(csv_path):
    with open(csv_path, encoding="utf-8", errors="replace") as f:
        lines2 = f.readlines()
    print(f"targets.csv: {len(lines2)}行")
    for l in lines2[:5]:
        print(" ", l.strip())
else:
    print("targets.csv: NOT FOUND")
