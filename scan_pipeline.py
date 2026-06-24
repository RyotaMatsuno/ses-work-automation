path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

keywords = ["processed_id", "drive_url", "spreadsheet", "retry", "Drive", "PATCH ERROR", "except", "continue"]
for i, line in enumerate(lines, 1):
    for kw in keywords:
        if kw.lower() in line.lower():
            print(f"{i}: {line.rstrip()}")
            break
