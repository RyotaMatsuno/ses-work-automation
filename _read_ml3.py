import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 5159付近を直接読む
with open("line_webhook/matching_logic.py", "rb") as f:
    raw = f.read()

chunk = raw[4800:5800]
print("=== raw bytes 4800-5800 ===")
# まずcp932でデコード試み
try:
    print(chunk.decode("cp932"))
except:
    print(chunk.decode("utf-8", errors="replace"))
