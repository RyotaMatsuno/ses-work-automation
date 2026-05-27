
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\matching_v2.py"
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

# judge_with_cache 前後を表示（124行目から30行分）
for i in range(123, 160):
    print(f"{i+1}: {lines[i]}", end="")
