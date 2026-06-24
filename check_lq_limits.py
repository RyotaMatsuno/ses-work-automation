# -*- coding: utf-8 -*-
# line_webhook/line_query.pyのTOP_LIMITとLINE_LIMITを確認
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if any(k in line for k in ["TOP_LIMIT", "LINE_LIMIT", "_limit_reply", "limit"]):
        print(f"L{i + 1}: {line.rstrip()}", flush=True)
