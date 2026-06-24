path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\notify_line.py"
with open(path, encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines[:80]):
    print(f"{i + 1}: {line}", end="")
