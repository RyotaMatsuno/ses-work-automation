import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

with open(os.path.join(BASE, "line_webhook/webhook_server.py"), encoding="utf-8") as f:
    lines = f.readlines()

# process_message関数の全体を抽出（L1830から100行）
print("=== process_message関数 ===", flush=True)
for i in range(1829, min(1830 + 120, len(lines))):
    print(f"L{i + 1}: {lines[i]}", end="", flush=True)
