import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("line_query/line_query.py", "rb") as f:
    raw = f.read()
content = raw.decode("cp932", errors="replace")

# VAL_ACTIVE / VAL_RECRUITING の定義を全部出す
import re

for m in re.finditer(r"VAL_\w+\s*=.*", content):
    print(m.group())

print()
# PROP_STA / PROP_INI の定義
for m in re.finditer(r"PROP_\w+\s*=.*", content):
    print(m.group())
