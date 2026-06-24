import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import os

# line_webhook/line_query.py の全内容を表示
paths = [
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py",
]

for p in paths:
    if os.path.exists(p):
        print(f"\n{'=' * 60}")
        print(f"FILE: {p}")
        print(f"SIZE: {os.path.getsize(p)} bytes")
        print("=" * 60)
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        print(content)
    else:
        print(f"NOT FOUND: {p}")
