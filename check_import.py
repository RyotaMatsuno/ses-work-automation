import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

# structurer.py の cost_guard import を確認
print("=== structurer.py の先頭30行 ===")
st = base / "matching_v3" / "structurer.py"
lines = st.read_text(encoding="utf-8", errors="replace").splitlines()
for i, l in enumerate(lines[:30], 1):
    print(f"  {i}: {l}")

# matching_v3.py の先頭30行（sys.path確認）
print("\n=== matching_v3.py 先頭30行 ===")
mv3 = base / "matching_v3" / "matching_v3.py"
for i, l in enumerate(mv3.read_text(encoding="utf-8", errors="replace").splitlines()[:30], 1):
    print(f"  {i}: {l}")

# cost_guard.py に CostGuard クラスがあるか確認
print("\n=== cost_guard.py CostGuardクラス確認 ===")
cg = base / "cost_guard.py"
cg_text = cg.read_text(encoding="utf-8", errors="replace")
for i, l in enumerate(cg_text.splitlines(), 1):
    if "class CostGuard" in l or "def can_call" in l or "def can_spend" in l:
        print(f"  Line {i}: {l.strip()}")
