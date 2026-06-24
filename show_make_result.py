# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

p2 = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\matching_v2.py"
lines2 = open(p2, encoding="utf-8").readlines()

print("=== make_project_result (264行~) ===")
for i in range(263, 310):
    print(f"{i + 1}: {lines2[i]}", end="")
