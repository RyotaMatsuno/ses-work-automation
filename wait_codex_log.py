import os
import time

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\codex_linequery_bugfix.log"
print("Waiting 90s for Codex...")
time.sleep(90)

size = os.path.getsize(log_path)
print(f"log size: {size} bytes")
with open(log_path, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()
print(f"lines: {len(lines)}")
for l in lines[-40:]:
    print(l, end="")
