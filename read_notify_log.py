import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
time.sleep(60)
with open("notify_line_test.log", "r", encoding="utf-8", errors="replace") as f:
    print(f.read())
