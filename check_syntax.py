import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

r = subprocess.run(
    ["python", "-c", "import py_compile; py_compile.compile('matching_v3/structurer.py', doraise=True)"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=str(base),
)
print(r.stderr.strip())
