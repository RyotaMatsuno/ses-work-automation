path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\skill_judge.py"
with open(path, encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    print(f"{i + 1}: {line}", end="")
