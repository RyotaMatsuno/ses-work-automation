import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

ses = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
lq_path = os.path.join(ses, "line_webhook", "line_query.py")
with open(lq_path, encoding="utf-8") as f:
    lines = f.readlines()

print(f"line_query.py: {len(lines)} lines")
print()

# 全体を出力（23KB程度なので全部読む）
for i, line in enumerate(lines, 1):
    print(f"L{i}: {line}", end="")
