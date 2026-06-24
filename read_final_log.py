import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("cleanup_final.log", "r", encoding="cp932", errors="replace") as f:
    lines = f.readlines()
print(f"行数: {len(lines)}")
print("全内容:")
print("".join(lines))
