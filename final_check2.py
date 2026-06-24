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

from line_query import PROP_OPTSK, handle_line_query

print(f'PROP_OPTSK = "{PROP_OPTSK}"')
print()
print("=== HS 北小金 最終出力 ===")
result = handle_line_query("HS 北小金")
print(result[:1500] if result else "None")
