# -*- coding: utf-8 -*-
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# L1927〜L1935の内容を確認
print("=== L1920〜L1945 ===")
for i, line in enumerate(lines[1919:1945], 1920):
    print(f"L{i}: {repr(line)}")
