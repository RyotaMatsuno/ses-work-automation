import sys

sys.stdout.reconfigure(encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\deploy_cloudrun.py"
with open(path, encoding="utf-8") as f:
    print(f.read())
