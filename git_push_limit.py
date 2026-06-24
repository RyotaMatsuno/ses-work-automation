import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# git add & commit
cmds = [
    "git add line_webhook/line_query.py",
    'git commit -m "fix: マッチング結果を上位15件（案件）/10件（人員）に制限"',
    "git push origin main",
]
for cmd in cmds:
    r = subprocess.run(cmd, shell=True, capture_output=True, cwd=cwd)
    out = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
    print(f"$ {cmd}\n{out.strip()}\n")
