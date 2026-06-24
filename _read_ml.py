import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("line_webhook/matching_logic.py", encoding="utf-8", errors="replace") as f:
    content = f.read()

# 「マッチ案件なし」周辺を抽出
idx = content.find("マッチ案件なし")
if idx != -1:
    print("=== 「マッチ案件なし」生成箇所 ===")
    print(content[max(0, idx - 500) : idx + 800])
else:
    # cp932で試す
    with open("line_webhook/matching_logic.py", encoding="cp932", errors="replace") as f:
        content2 = f.read()
    idx2 = content2.find("マッチ案件なし")
    if idx2 != -1:
        print("=== (cp932) ===")
        print(content2[max(0, idx2 - 500) : idx2 + 800])

# 通知メッセージ全体の構造も確認
print("\n\n=== build_match_message 関数全体 ===")
import re

m = re.search(r"def build_match_message.*?(?=\ndef |\Z)", content, re.DOTALL)
if m:
    print(m.group()[:3000])
