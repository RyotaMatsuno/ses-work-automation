import os

base = "C:/Users/ma_py/OneDrive/デスクトップ/ses_work"
path = os.path.join(base, "mail_pipeline.py")
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

keywords = [
    "案件詳細",
    "業務内容",
    "description",
    "本文",
    "raw_body",
    "email_body",
    "full_text",
    "truncat",
    "slice",
    "[:",
]
for i, line in enumerate(lines):
    if any(k in line for k in keywords):
        print(f"{i + 1}: {line}", end="")
