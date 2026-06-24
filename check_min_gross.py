import sys

sys.stdout.reconfigure(encoding="utf-8")
with open("matching_v2/matching_v2.py", encoding="utf-8") as f:
    content = f.read()
lines = content.split("\n")
for i, line in enumerate(lines):
    if "get_min_gross" in line or "okamoto" in line.lower() or "return 3" in line or "岡本" in line:
        print(f"{i + 1}: {repr(line)}")
