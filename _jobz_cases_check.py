import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# matching_v3/notion_client.py の get_new_cases で days=4 のフィルタ内容確認
SES = os.getcwd()
nc = os.path.join(SES, "matching_v3", "notion_client.py")
with open(nc, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

print("■ get_new_cases 関数")
in_func = False
count = 0
for i, line in enumerate(lines, 1):
    if "def get_new_cases" in line:
        in_func = True
    if in_func:
        print(f"  L{i}: {line.rstrip()}")
        count += 1
    if in_func and count > 5 and line.strip().startswith("def "):
        break
