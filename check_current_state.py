# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# mail_pipeline.py の FETCH_LIMIT確認
import re

p1 = BASE + r"\mail_pipeline\mail_pipeline.py"
c1 = open(p1, encoding="utf-8").read()
for m in re.finditer(r"(FETCH_LIMIT|PROCESS_LIMIT)\s*=\s*\d+", c1):
    print(f"pipeline: {m.group()}")

# matching_v2.pyのraw_body周辺確認
p2 = BASE + r"\matching_v2\matching_v2.py"
lines2 = open(p2, encoding="utf-8").readlines()
print("\nmatching_v2.py raw_body周辺:")
for i in range(225, 265):
    print(f"{i + 1}: {lines2[i]}", end="")

# result.jsonにraw_bodyが含まれているか確認
import json

result_path = BASE + r"\matching_v2\result.json"
data = json.load(open(result_path, encoding="utf-8"))
if data:
    item = data[0]
    print(f"\nresult.json[0] keys: {list(item.keys())}")
    if "raw_body" in item:
        print(f"raw_body length: {len(item['raw_body'])}")
        print(f"raw_body preview: {item['raw_body'][:200]}")
    else:
        print("raw_body: NOT in result.json")
    if item.get("candidates"):
        c = item["candidates"][0]
        print(f"candidate keys: {list(c.keys())}")
