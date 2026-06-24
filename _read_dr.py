import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
# daily_report.pyから既存push関数を確認
with open("daily_report.py", encoding="utf-8") as f:
    content = f.read()
# push関数定義部分を抽出
idx = content.find("def ")
while idx != -1:
    end = content.find("\n\n", idx)
    chunk = content[idx : end if end != -1 else idx + 500]
    if "push" in chunk[:50].lower() or "line" in chunk[:50].lower():
        print(chunk[:600])
        print("---")
    idx = content.find("def ", idx + 5)
