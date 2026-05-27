import time, os, sys, subprocess
sys.stdout.reconfigure(encoding='utf-8')

time.sleep(120)

for label, logfile in [
    ("webhook", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_affiliation.log"),
    ("composer", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_composer.log"),
]:
    size = os.path.getsize(logfile)
    print(f"\n=== {label} ({size}bytes) ===")
    if size > 0:
        with open(logfile, "r", encoding="utf-8", errors="replace") as f:
            print(f.read()[-500:])
    else:
        print("(still running)")

# pipeline動作確認
r = subprocess.run(
    ["python", "pipeline.py", "--dry-run"],
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1",
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print(f"\npipeline: {r.stdout.strip()}")
if r.returncode != 0:
    print(f"ERR: {r.stderr[-300:]}")
