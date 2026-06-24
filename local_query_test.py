import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Cloud Run環境での文字化けを確認するため、
# line_query.py をローカルで直接実行してNotionへの実通信テストを行う
# → 「HS 北小金」の結果をそのままLINEにpushする

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
for k, v in config.items():
    os.environ.setdefault(k, v)

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
for m in list(sys.modules):
    if "line_query" in m:
        del sys.modules[m]

print("line_query ローカル実行テスト開始...")
from line_query import handle_line_query

result = handle_line_query("HS 北小金")
print(f"結果タイプ: {type(result).__name__}")
print(f"結果長: {len(result) if result else 0}文字")
print()
print("=== 結果 ===")
print(result if result else "(None)")
