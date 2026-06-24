import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

lines = open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline.py", encoding="utf-8").readlines()
keywords = ["price", "Price", "number", "tanaka", "register_project", "register_engineer", "Notion"]
for i, l in enumerate(lines, 1):
    if any(k in l for k in keywords):
        print(f"{i}: {l}", end="")
