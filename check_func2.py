import sys

sys.stdout.reconfigure(encoding="utf-8")
with open("matching_v2/matching_v2.py", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines[248:290], start=249):
    print(f"{i}: {repr(line.rstrip())}")
