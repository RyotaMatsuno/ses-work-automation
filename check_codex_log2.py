import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
time.sleep(60)
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\codex_matching_v2.log"
size = os.path.getsize(log_path)
print(f"log size: {size} bytes")
with open(log_path, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()
print(f"total lines: {len(lines)}")
for line in lines[-30:]:
    print(line, end="")
