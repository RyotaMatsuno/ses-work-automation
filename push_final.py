import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# git statusとremoteとの差分を確認してからpush
cmds = [
    "git status --short",
    "git push origin main",
]
for cmd in cmds:
    r = subprocess.run(cmd, shell=True, capture_output=True, cwd=cwd)
    out = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
    print(f"$ {cmd}\n{out.strip()}\n")
