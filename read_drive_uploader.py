import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# 1. drive_uploader.pyの内容確認
print("=== drive_uploader.py ===", flush=True)
with open(os.path.join(BASE, "drive_uploader.py"), encoding="utf-8") as f:
    print(f.read(), flush=True)
