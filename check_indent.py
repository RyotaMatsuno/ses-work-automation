import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
st_path = base / "matching_v3" / "structurer.py"
lines = st_path.read_text(encoding="utf-8", errors="replace").splitlines()

# Line 44〜58付近を確認
print("=== Line 44-58 ===")
for i, l in enumerate(lines[43:58], 44):
    print(f"  {i}: {repr(l)}")
