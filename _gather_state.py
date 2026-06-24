import datetime
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
B = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"


def show(f, n=50):
    p = os.path.join(B, f)
    print("=" * 10, f, "=" * 10)
    if os.path.exists(p):
        print("\n".join(open(p, encoding="utf-8", errors="replace").read().splitlines()[-n:]))
    else:
        print("(なし)")


show("_audit_fix_report.txt", 60)
show("_finalizer_report.txt", 12)
show("_run2100_report.txt", 22)
print("=" * 10, "git log -10", "=" * 10)
r = subprocess.run(
    ["git", "-C", B, "log", "--oneline", "-10"], capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print(r.stdout or r.stderr)
print("now:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
