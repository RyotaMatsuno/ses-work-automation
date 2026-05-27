
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\matching_v2.py"
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

# extract_engineer関数の中身を表示（204行目から30行分）
for i in range(203, 240):
    print(f"{i+1}: {lines[i]}", end="")
