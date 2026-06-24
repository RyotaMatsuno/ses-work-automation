# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

p2 = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\matching_v2.py"
lines = open(p2, encoding="utf-8").readlines()

# get_text_property / get_rich_text 関数を探す
for i, line in enumerate(lines):
    if "def get_text_property" in line or "def get_rich_text" in line:
        print(f"{i + 1}: {line}", end="")
        for j in range(i + 1, i + 12):
            print(f"{j + 1}: {lines[j]}", end="")
        print()
