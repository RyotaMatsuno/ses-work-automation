import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# バイナリとして読んでUnicode確認
with open("matching_v3/matching_v3.py", "rb") as f:
    raw = f.read()

target = "マッチ案件なし".encode("utf-8")
idx = raw.find(target)
print(f"utf-8 search: {idx}")

target2 = "マッチ案件なし".encode("cp932")
idx2 = raw.find(target2)
print(f"cp932 search: {idx2}")

# 先ほどFOUNDと出たのにre.finditerで出なかった謎を解明
# processed_db.pyで確認
with open("matching_v3/processed_db.py", encoding="utf-8", errors="replace") as f:
    content = f.read()

import re

hits = list(re.finditer(r"マッチ案件なし", content))
print(f"\nprocessed_db.py hits: {len(hits)}")
for h in hits:
    print(content[max(0, h.start() - 300) : h.end() + 300])
