import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

print("=== wd_matching_v3.bat 再テスト ===")
r = subprocess.run(
    ["cmd", "/c", str(base / "wd_matching_v3.bat")],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=60,
)
print(f"returncode: {r.returncode}")
out = (r.stdout + r.stderr).strip()
for l in out.splitlines()[:30]:
    print(f"  {l}")
