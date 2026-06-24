# judge_with_cache の場所を確認
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\matching_v2.py"
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "judge_with_cache" in line or "judge_skills" in line:
        print(f"{i + 1}: {line}", end="")
