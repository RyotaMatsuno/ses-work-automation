import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

# _call_openai の定義位置と structure()内の呼び出し位置を確認
st = base / "matching_v3" / "structurer.py"
lines = st.read_text(encoding="utf-8", errors="replace").splitlines()
for i, l in enumerate(lines, 1):
    if "def _call_openai" in l or ("_call_openai" in l and "def " not in l):
        print(f"  Line {i}: {l.strip()}")

# structure()関数全体（Line35から）
print("\n=== structure() Line35〜70 ===")
for i, l in enumerate(lines[34:70], 35):
    print(f"  {i}: {l}")
