import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("mail_pipeline/mail_pipeline.py", encoding="utf-8", errors="replace") as f:
    content = f.read()

# LLM分類 + フォールバック周辺を抽出
for kw in ["call_claude", "classify", "def classify", "LLM分類", "other", "fallback"]:
    m = re.search(rf".{{0,50}}{kw}.{{0,300}}", content, re.DOTALL)
    if m:
        idx = content.find(kw)
        print(f"=== [{kw}] at {idx} ===")
        print(content[max(0, idx - 200) : idx + 600])
        print()
        break

# classify関数全体を探す
m = re.search(r"def classify.*?(?=\ndef |\Z)", content, re.DOTALL)
if m:
    print("=== def classify ===")
    print(m.group()[:3000])
