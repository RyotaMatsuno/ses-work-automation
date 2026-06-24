# -*- coding: utf-8 -*-
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# matchingのログ確認
log = open(
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_run_test.log", encoding="utf-8", errors="replace"
).read()
print("=== matching log (末尾) ===")
print(log[-1000:])

# result.jsonを確認
data = json.load(open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\result.json", encoding="utf-8"))
print(f"\nresult.json: {len(data)}件")
if data:
    item = data[0]
    print(f"keys: {list(item.keys())}")
    rb = item.get("raw_body", None)
    if rb is None:
        print("raw_body: キーなし")
    else:
        print(f"raw_body length: {len(rb)}")
        print(f"raw_body preview: {rb[:200]}")
