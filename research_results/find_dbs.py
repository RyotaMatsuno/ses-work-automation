import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os

SES_WORK = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
print("=== ALL .db FILES ===")
for root, dirs, files in os.walk(SES_WORK):
    for f in files:
        if f.endswith('.db'):
            fpath = os.path.join(root, f)
            sz = os.path.getsize(fpath)
            print(f"  {fpath} ({sz/1024:.0f}KB)")

# Also check AppData
APPDATA = r"C:\Users\ma_py\AppData\Local\ses_work_state"
if os.path.exists(APPDATA):
    print(f"\n=== {APPDATA} ===")
    for f in os.listdir(APPDATA):
        fpath = os.path.join(APPDATA, f)
        sz = os.path.getsize(fpath) if os.path.isfile(fpath) else 0
        print(f"  {f} ({sz/1024:.0f}KB)")
