import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"

with open(os.path.join(BASE, "line_query.py"), encoding="utf-8") as f:
    content = f.read()

# 主要な関数名と構造だけ抽出
lines = content.splitlines()
print(f"総行数: {len(lines)}", flush=True)
print("", flush=True)

# def行とコメント行だけ
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("def ") or stripped.startswith("class ") or (stripped.startswith("#") and len(stripped) > 3):
        print(f"L{i + 1}: {line.rstrip()}", flush=True)
