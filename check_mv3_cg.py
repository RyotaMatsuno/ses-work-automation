import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
mv3_dir = base / "matching_v3"

# matching_v3/cost_guard.py の中身（CostGuardクラス）
print("=== matching_v3/cost_guard.py ===")
mv3_cg = mv3_dir / "cost_guard.py"
print(mv3_cg.read_text(encoding="utf-8", errors="replace"))
