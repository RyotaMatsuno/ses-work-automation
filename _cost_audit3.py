import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

print("=" * 60)
print("【4】cost_guard.py vs .env vs common/ledger.py 整合性検証")
print("=" * 60)

# cost_guard.py の全定数・上限値を抽出
with open("cost_guard.py", encoding="utf-8") as f:
    cg = f.read()

print("\n  cost_guard.py のLIMIT関連全行:")
for i, line in enumerate(cg.split("\n"), 1):
    stripped = line.strip()
    if any(
        k in stripped for k in ["LIMIT", "DAILY", "MONTHLY", "environ", "getenv", "LLM_KILL"]
    ) and not stripped.startswith("#"):
        print(f"    L{i}: {stripped[:120]}")

# common/ledger.py
print()
if os.path.exists("common/ledger.py"):
    with open("common/ledger.py", encoding="utf-8") as f:
        ledger = f.read()
    print("  common/ledger.py のLIMIT関連全行:")
    for i, line in enumerate(ledger.split("\n"), 1):
        stripped = line.strip()
        if any(
            k in stripped for k in ["LIMIT", "DAILY", "MONTHLY", "environ", "getenv", "can_spend"]
        ) and not stripped.startswith("#"):
            print(f"    L{i}: {stripped[:120]}")
else:
    print("  common/ledger.py: なし")

# mail_pipeline の ledger import元
print()
print("  mail_pipeline が参照するledger:")
with open("mail_pipeline/mail_pipeline.py", encoding="utf-8") as f:
    mp = f.read()
for line in mp.split("\n"):
    if "ledger" in line.lower() and ("import" in line or "from" in line):
        print(f"    {line.strip()}")
