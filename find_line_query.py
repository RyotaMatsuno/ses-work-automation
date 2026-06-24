import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# line_queryモジュールを探す
for root, dirs, files in os.walk(BASE):
    for f in files:
        if "line_query" in f or "line_query" in root:
            print(os.path.join(root, f), flush=True)
