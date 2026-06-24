import sys

sys.stdout.reconfigure(encoding="utf-8")
with open("matching_v2/matching_v2.py", encoding="utf-8") as f:
    lines = f.readlines()
# 520行前後を確認
for i, line in enumerate(lines[515:545], start=516):
    print(f"{i}: {repr(line.rstrip())}")
