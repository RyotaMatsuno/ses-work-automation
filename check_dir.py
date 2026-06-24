import os

target = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\flag_auto_updater"
if os.path.exists(target):
    files = os.listdir(target)
    print("EXISTS")
    for f in sorted(files):
        print(f)
else:
    print("NOT FOUND")
