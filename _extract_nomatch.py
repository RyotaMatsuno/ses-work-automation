import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("matching_v3/matching_v3.py", encoding="utf-8", errors="replace") as f:
    content = f.read()

# match_result系の部分を全部抽出
import re

# "マッチ案件なし"の全出現箇所
for m in re.finditer(r".{0,300}マッチ案件なし.{0,300}", content, re.DOTALL):
    print("=== MATCH ===")
    print(m.group())
    print()
