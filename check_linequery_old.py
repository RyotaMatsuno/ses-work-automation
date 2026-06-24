# -*- coding: utf-8 -*-
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# _limit_reply関数を探す
idx = content.find("_limit_reply")
if idx >= 0:
    # 前後200文字表示
    start = max(0, idx - 50)
    end = min(len(content), idx + 300)
    print("=== _limit_reply in line_query/line_query.py ===")
    print(content[start:end])
else:
    print("_limit_reply NOT FOUND")

# LINE_LIMITも探す
for keyword in ["LINE_LIMIT", "TOP_LIMIT", "limit_reply", "LIMIT"]:
    idx2 = content.find(keyword)
    if idx2 >= 0:
        print(f"\n=== {keyword} found at {idx2} ===")
        print(content[max(0, idx2 - 20) : idx2 + 100])
