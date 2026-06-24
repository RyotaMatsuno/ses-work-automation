import os

archive = r"C:\Users\ma_py\OneDrive\Desktop\ses_work\usage_tracker\cost_log_archive_2026-06.jsonl"
if not os.path.exists(archive):
    print(f"Not found: {archive}")
    # try alternate
    archive2 = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log_archive_2026-06.jsonl"
    archive = archive2

count = 0
sample = []
with open(archive, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        count += 1
        if count <= 3:
            sample.append(line[:200])

print(f"Total lines: {count}")
for s in sample:
    print(s)
