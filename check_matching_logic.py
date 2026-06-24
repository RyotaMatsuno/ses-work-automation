path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\matching_v2.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

keywords = ["batch", "BATCH", "skip", "filter", "rule", "keyword", "prefilter", "上位", "絞り", "limit", "top"]
for i, line in enumerate(lines, 1):
    if any(kw.lower() in line.lower() for kw in keywords):
        print(f"{i}: {line.rstrip()}")
