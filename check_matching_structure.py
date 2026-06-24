# matching_v2の1回の呼び出しが何をしているか確認
# matching_v2/matching_v2.pyの構造を見る
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\matching_v2.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"総行数: {len(lines)}")
# API呼び出し箇所とループ構造を確認
for i, line in enumerate(lines, 1):
    if any(kw in line for kw in ["client.messages", "anthropic", "for ", "while ", "batch", "engineer", "project"]):
        if any(kw in line for kw in ["client.messages", "for ", "batch"]):
            print(f"{i}: {line.rstrip()}")
