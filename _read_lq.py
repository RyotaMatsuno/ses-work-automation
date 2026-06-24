import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# line_query/line_query.py を確認 - handle_line_queryとPH処理
with open("line_query/line_query.py", "rb") as f:
    raw = f.read()
content = raw.decode("cp932", errors="replace")

# engineer_query と handle_line_query の実装
import re

for fn in ["engineer_query", "handle_line_query", "project_query"]:
    m = re.search(rf"def {fn}.*?(?=\ndef |\Z)", content, re.DOTALL)
    if m:
        print(f"=== def {fn} ===")
        print(m.group()[:2000])
        print()
