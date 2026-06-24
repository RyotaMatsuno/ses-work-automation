import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
st = base / "matching_v3" / "structurer.py"
lines = st.read_text(encoding="utf-8", errors="replace").splitlines()

for i, l in enumerate(lines, 1):
    if l.startswith("def "):
        print(f"  Line {i}: {l.strip()}")

# 実際にimportしてみる
print("\n=== import test ===")
import subprocess

r = subprocess.run(
    [
        "python",
        "-c",
        "import sys; sys.path.insert(0,'matching_v3'); sys.path.insert(0,'.'); "
        "from structurer import _call_openai; print('OK')",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=str(base),
)
print(r.stdout.strip())
print(r.stderr.strip()[:200])
