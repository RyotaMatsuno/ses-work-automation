
import os

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
path = os.path.join(base, "mail_pipeline", "mail_pipeline.py")
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

# note = f"..." の行を探す
for i, line in enumerate(lines):
    if 'note = f' in line and 'sender' in line:
        print(f"{i+1}: {repr(line)}")
