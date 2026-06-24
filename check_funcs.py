import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
# 公開関数名確認
st = base / "matching_v3" / "structurer.py"
for i, l in enumerate(st.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
    if l.startswith("def ") or l.startswith("class "):
        print(f"  Line {i}: {l.strip()}")
