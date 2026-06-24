path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\skill_judge.py"
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

# 276行目周辺を確認
for i in range(273, 290):
    print(f"{i + 1}: {repr(lines[i])}")
