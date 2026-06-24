# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# FETCH_LIMIT / PROCESS_LIMIT の設定値確認
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py"
lines = open(path, encoding="utf-8").readlines()
for i, line in enumerate(lines):
    if any(k in line for k in ["FETCH_LIMIT", "PROCESS_LIMIT", "MATCH_TOP_N", "limit", r"ALL\|", "SINCE", "search"]):
        if i < 400:
            print(f"{i + 1}: {line}", end="")

# notify_line.pyにraw_bodyを渡す仕組みがあるか
print("\n=== notify_line.py → raw_body / original_text ===")
nl_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\notify_line.py"
nl_lines = open(nl_path, encoding="utf-8").readlines()
for i, line in enumerate(nl_lines):
    if any(k in line for k in ["raw", "original", "body", "本文", "full_text"]):
        print(f"{i + 1}: {line}", end="")
