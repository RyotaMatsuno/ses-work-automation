
import os

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
path = os.path.join(base, "mail_pipeline", "mail_pipeline.py")
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

# 524行目と554行目を確認して修正
for i in [522, 523, 524, 525, 552, 553, 554, 555]:
    print(f"{i+1}: {repr(lines[i])}")
