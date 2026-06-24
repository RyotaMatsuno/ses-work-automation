import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\codex_phase_e.log"
print("Waiting 75 seconds for Codex...")
time.sleep(75)
if os.path.exists(log):
    size = os.path.getsize(log)
    print(f"Log size: {size} bytes")
    with open(log, encoding="utf-8", errors="replace") as f:
        content = f.read()
    print(content[-3000:] if len(content) > 3000 else content)
else:
    print("Log file not found yet")
