import time, os, sys
sys.stdout.reconfigure(encoding='utf-8')

time.sleep(180)

for label, logfile, pydir in [
    ("webhook affiliation", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_affiliation.log",
     r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"),
    ("composer", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_composer.log",
     r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1"),
]:
    size = os.path.getsize(logfile)
    print(f"\n=== {label} log ({size}bytes) ===")
    if size > 0:
        with open(logfile, "r", encoding="utf-8", errors="replace") as f:
            print(f.read()[-800:])
    else:
        print("(empty)")
