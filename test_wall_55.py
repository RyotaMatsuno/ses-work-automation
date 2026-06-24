import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

r = subprocess.run(
    [
        "python",
        "wall_hitting.py",
        "--problem",
        "Cloud RunにデプロイしたPythonアプリがローカルでは動くが本番で500エラーになる",
    ],
    capture_output=True,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    timeout=90,
)
print(r.stdout.decode("utf-8", errors="replace"))
if r.returncode != 0:
    print("STDERR:", r.stderr.decode("utf-8", errors="replace")[:300])
print("RC:", r.returncode)
