import time, os

time.sleep(180)  # 3分待機

for logfile in [
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\pipeline_v1_run.log",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\outreach_system_run.log"
]:
    print(f"\n=== {os.path.basename(logfile)} ===")
    try:
        with open(logfile, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if content.strip():
            print(content[-3000:])
        else:
            print("(still empty)")
    except Exception as e:
        print(f"ERROR: {e}")

# pipeline_v1のファイル確認
print("\n=== pipeline_v1/ files ===")
import glob
files = glob.glob(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1\*.py")
for f in files:
    print(os.path.basename(f))
print("(outreach_system)")
files2 = glob.glob(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\outreach_system\*.py")
for f in files2:
    print(os.path.basename(f))
