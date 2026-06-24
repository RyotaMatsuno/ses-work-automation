import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("line_webhook/line_bridge.py", "rb") as f:
    raw = f.read()
content = raw.decode("cp932", errors="replace")

# classify_route の全文
import re

m = re.search(r"def classify_route.*?(?=\ndef |\Z)", content, re.DOTALL)
if m:
    print("=== classify_route ===")
    print(m.group()[:3000])

# route_line_message の全文
m2 = re.search(r"def route_line_message.*?(?=\ndef |\Z)", content, re.DOTALL)
if m2:
    print("\n=== route_line_message ===")
    print(m2.group()[:3000])
