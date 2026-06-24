import sys

sys.stdout.reconfigure(encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

# L805-L812 の所属情報セット部分を確認
print("=== L800-L825: affiliation block ===")
for i in range(799, 825):
    if i < len(lines):
        print(f"L{i + 1}: {lines[i]}", end="")
