import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"

with open(os.path.join(BASE, "line_query.py"), encoding="utf-8") as f:
    lines = f.readlines()

# handle_line_query(L472)〜 と classify_query(L131)〜 と project_query(L367)〜 と format_engineer_result(L451)〜 を表示
for section in [(130, 160), (367, 430), (451, 498), (472, 530), (608, 664)]:
    s, e = section
    print(f"\n=== L{s + 1}〜L{e} ===", flush=True)
    for i in range(s, min(e, len(lines))):
        print(f"L{i + 1}: {lines[i]}", end="", flush=True)
