import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
with open("cost_guard.py", encoding="utf-8") as f:
    content = f.read()
# get_costs()とcan_spend相当の部分を確認
idx = content.find("def get_costs")
print(content[idx : idx + 1500])
