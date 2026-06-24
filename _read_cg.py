import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
with open("cost_guard.py", encoding="utf-8") as f:
    content = f.read()
# can_spend()の仕様だけ抜粋
lines = content.split("\n")
for i, line in enumerate(lines):
    if "can_spend" in line or "def " in line or "class " in line:
        print(f"{i + 1}: {line}")
