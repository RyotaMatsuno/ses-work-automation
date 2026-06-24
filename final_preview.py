import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
for k, v in config.items():
    os.environ.setdefault(k, v)

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
for m in list(sys.modules):
    if "line_query" in m:
        del sys.modules[m]
from line_query import handle_line_query

print("=== HS 北小金 最終出力確認 ===")
result = handle_line_query("HS 北小金")
print(result if result else "None")
print()
print(f"文字数: {len(result) if result else 0}")
