import sys

sys.stdout.reconfigure(encoding="utf-8")

import os

# webhook_server.py を探す
for root, dirs, files in os.walk(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"):
    for f in files:
        if "webhook" in f.lower() and f.endswith(".py"):
            full = os.path.join(root, f)
            size = os.path.getsize(full)
            print(f"{full} ({size} bytes)")
