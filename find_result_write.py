# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

p2 = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\matching_v2.py"
lines = open(p2, encoding="utf-8").readlines()

# make_project_result をもう一度探す（複数定義がないか）
for i, line in enumerate(lines):
    if "make_project_result" in line or "result_item" in line or "write_result" in line:
        print(f"{i + 1}: {line}", end="")

# また result.json を書き出している部分を探す
for i, line in enumerate(lines):
    if "result.json" in line or "json.dump" in line or "write" in line.lower() and "result" in line:
        print(f"WRITE {i + 1}: {line}", end="")
