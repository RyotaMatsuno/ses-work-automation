import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
with open("gate_checker/agreement_checker.py", encoding="utf-8") as f:
    content = f.read()
print(content[:3000])
