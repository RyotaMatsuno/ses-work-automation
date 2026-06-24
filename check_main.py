import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
with open(r"freee/payment_checker.py", "r", encoding="utf-8") as f:
    src = f.read()

# main()のrun()呼び出し箇所を確認
import re

matches = [(m.start(), src[m.start() : m.start() + 200]) for m in re.finditer(r"def main", src)]
for pos, snippet in matches:
    print(f"pos={pos}")
    print(snippet)
    print("---")
