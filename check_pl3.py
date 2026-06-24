import os

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
path = os.path.join(base, "mail_pipeline", "mail_pipeline.py")
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# 案件詳細・業務内容・本文・truncate・sliceに関係する行を探す
keywords = [
    "案件詳細",
    "業務内容",
    "raw_body",
    "email_body",
    "full_body",
    "body",
    "truncat",
    "slice",
    "[:2000",
    "[:1000",
    "[:500",
    "description",
    "register_project",
    "notion",
    "properties",
]
for i, line in enumerate(lines):
    if any(k in line for k in keywords):
        print(f"{i + 1}: {line}", end="")
