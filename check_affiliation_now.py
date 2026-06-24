import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

for label, logfile in [
    ("webhook affiliation", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_affiliation.log"),
    ("composer", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_composer.log"),
]:
    size = os.path.getsize(logfile)
    print(f"\n=== {label} ({size}bytes) ===")
    if size > 0:
        with open(logfile, "r", encoding="utf-8", errors="replace") as f:
            print(f.read()[-800:])
    else:
        print("(still running)")

# composer.pyの変更確認
import subprocess

result = subprocess.run(
    ["python", "-c", "from composer import attach_drafts; print('import OK')"],
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1",
    capture_output=True,
    text=True,
    encoding="utf-8",
)
print(f"\ncomposer import: {result.stdout.strip() or result.stderr.strip()[:200]}")
