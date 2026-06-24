import glob
import os

for logfile in [
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\pipeline_v1_run.log",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\outreach_system_run.log",
]:
    print(f"\n=== {os.path.basename(logfile)} ({os.path.getsize(logfile)} bytes) ===")
    try:
        with open(logfile, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        print(content[-2000:] if content.strip() else "(empty)")
    except Exception as e:
        print(f"ERROR: {e}")

print("\n=== pipeline_v1/ .py files ===")
for f in glob.glob(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1\*.py"):
    print(os.path.basename(f))

print("\n=== outreach_system/ .py files ===")
for f in glob.glob(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\outreach_system\*.py"):
    print(os.path.basename(f))
