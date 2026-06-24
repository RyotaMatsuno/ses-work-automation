import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

lw = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"

# 構文チェック
r = subprocess.run(
    ["python", "-m", "py_compile", "line_query.py"], cwd=lw, capture_output=True, text=True, encoding="utf-8"
)
print(f"syntax: {'OK' if r.returncode == 0 else 'ERROR: ' + r.stderr}")

# テスト
sys.path.insert(0, lw)
os.chdir(lw)
if "line_query" in sys.modules:
    del sys.modules["line_query"]
from line_query import handle_line_query

print("\n=== HS 北小金 (粗利0〜15万のみ) ===")
result = handle_line_query("HS 北小金")
print(result if result else "(no result)")
