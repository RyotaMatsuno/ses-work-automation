import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
time.sleep(120)
log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee\codex_payment_checker.log"
with open(log, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()
print(content[-1500:] if len(content) > 1500 else content)
