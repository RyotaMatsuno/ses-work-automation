import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("line_query/line_query.py", "rb") as f:
    raw = f.read()
content = raw.decode("cp932", errors="replace")

# engineer_query の全文を丸ごと取得
import re

m = re.search(r"def engineer_query.*?(?=\ndef |\Z)", content, re.DOTALL)
if m:
    print(m.group())
