# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

p2 = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\matching_v2.py"
lines = open(p2, encoding="utf-8").readlines()

# 264~290行 (make_project_result全体)
print("=== make_project_result ===")
for i in range(263, 292):
    print(f"{i + 1}: {lines[i]}", end="")

# 480~495行 (json.dump周辺)
print("\n=== json.dump 周辺 ===")
for i in range(479, 496):
    print(f"{i + 1}: {lines[i]}", end="")
