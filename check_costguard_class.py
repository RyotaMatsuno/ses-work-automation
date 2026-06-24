import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

# cost_guard.py に CostGuard クラスが本当にないか全文検索
cg_text = (base / "cost_guard.py").read_text(encoding="utf-8", errors="replace")
print(f"cost_guard.py: {len(cg_text.splitlines())}行")
# classを全部列挙
for i, l in enumerate(cg_text.splitlines(), 1):
    if l.startswith("class ") or "class Cost" in l:
        print(f"  Line {i}: {l}")

# matching_v3/cost_guard.py が別に存在するか確認
print("\n=== matching_v3/cost_guard.py 確認 ===")
mv3_cg = base / "matching_v3" / "cost_guard.py"
if mv3_cg.exists():
    mv3_cg_text = mv3_cg.read_text(encoding="utf-8", errors="replace")
    print(f"  存在 ({mv3_cg.stat().st_size}bytes)")
    for i, l in enumerate(mv3_cg_text.splitlines(), 1):
        if "class CostGuard" in l or "def can_call" in l or "def can_spend" in l:
            print(f"  Line {i}: {l.strip()}")
else:
    print("  存在しない")
