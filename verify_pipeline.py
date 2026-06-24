import os

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
path = os.path.join(base, "mail_pipeline", "mail_pipeline.py")
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

checks = {
    "classify body limit 8000": False,
    "split_rich_text helper": False,
    "案件詳細 split_rich_text": False,
    "register_project raw_body param": False,
    "note uses raw_body": False,
    "call passes raw_body": False,
}

for i, line in enumerate(lines):
    if "body[:8000]" in line:
        checks["classify body limit 8000"] = True
    if "def split_rich_text" in line:
        checks["split_rich_text helper"] = True
    if "split_rich_text(note)" in line:
        checks["案件詳細 split_rich_text"] = True
    if 'raw_body: str = ""' in line:
        checks["register_project raw_body param"] = True
    if "raw_body or info.get" in line:
        checks["note uses raw_body"] = True
    if "raw_body=body" in line:
        checks["call passes raw_body"] = True

for k, v in checks.items():
    print(f"{'OK' if v else 'NG'}: {k}")
