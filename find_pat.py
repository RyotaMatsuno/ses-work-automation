import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# 実際のパターンを探す
for i, line in enumerate(src.split("\n"), 1):
    if "送信者" in line and "件名" in line:
        print(f"L{i}: {repr(line[:80])}")
