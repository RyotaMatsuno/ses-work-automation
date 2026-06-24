import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py"
lines = open(path, encoding="utf-8").readlines()
# classify_email関数の中身
print("".join(lines[463:530]))
print("...")
# main処理部分
print("".join(lines[850:950]))
