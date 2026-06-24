import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# line_webhook/line_query.py を確認
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"総行数: {len(lines)}")
for i, line in enumerate(lines, 1):
    if "def handle_line_query" in line:
        print(f"\n=== handle_line_query (L{i}) ===")
        for j, l in enumerate(lines[i - 1 : i + 15], i):
            print(f"L{j}: {l.rstrip()}")
        break

# classify_queryも確認
for i, line in enumerate(lines, 1):
    if "def classify_query" in line:
        print(f"\n=== classify_query (L{i}) ===")
        for j, l in enumerate(lines[i - 1 : i + 15], i):
            print(f"L{j}: {l.rstrip()}")
        break
