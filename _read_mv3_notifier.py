import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("matching_v3/notifier.py", encoding="utf-8", errors="replace") as f:
    content = f.read()
print(content[:5000])
