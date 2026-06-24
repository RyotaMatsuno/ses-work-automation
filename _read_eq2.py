import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("line_query/line_query.py", "rb") as f:
    raw = f.read()
content = raw.decode("cp932", errors="replace")

import re

# _match_station の実装を確認
m = re.search(r"def _match_station.*?(?=\ndef |\Z)", content, re.DOTALL)
if m:
    print("=== _match_station ===")
    print(m.group())

# _match_initial の実装を確認
m2 = re.search(r"def _match_initial.*?(?=\ndef |\Z)", content, re.DOTALL)
if m2:
    print("\n=== _match_initial ===")
    print(m2.group())

# classify_query の実装を確認（PHをどう解析するか）
m3 = re.search(r"def classify_query.*?(?=\ndef |\Z)", content, re.DOTALL)
if m3:
    print("\n=== classify_query ===")
    print(m3.group())

# PROP_WORKST / VAL_ACTIVE2 など定数を確認
for kw in ["VAL_ACTIVE", "VAL_RECRUIT", "PROP_WORKST", "PROP_STATUS", "VAL_ADJUSTING"]:
    idx = content.find(kw + " ")
    if idx == -1:
        idx = content.find(kw + "=")
    if idx != -1:
        print(f"\n{content[idx : idx + 100]}")
