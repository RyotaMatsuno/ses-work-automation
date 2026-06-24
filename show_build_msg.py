# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

p3 = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\notify_line.py"
lines = open(p3, encoding="utf-8").readlines()

# build_project_message 確認
for i in range(303, 380):
    print(f"{i + 1}: {lines[i]}", end="")
