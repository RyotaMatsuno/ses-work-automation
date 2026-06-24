# -*- coding: utf-8 -*-
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

for keyword in ["LINE_LIMIT", "TOP_LIMIT"]:
    idx = content.find(keyword)
    if idx >= 0:
        print(content[idx : idx + 60], flush=True)
    else:
        print(f"{keyword} NOT FOUND", flush=True)
