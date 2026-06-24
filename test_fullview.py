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

# ローカルテスト
sys.path.insert(0, lw)
os.chdir(lw)
if "line_query" in sys.modules:
    del sys.modules["line_query"]
from line_query import handle_line_query

result = handle_line_query("HS 北小金")
lines = result.split("\n") if result else []
print(f"\n件数行: {lines[0] if lines else '(none)'}")
print(f"総行数: {len(lines)}")
print(f"末尾3行: {lines[-3:]}")
# (上位5件表示) が消えているか確認
has_limit_msg = any("上位" in l or "表示" in l for l in lines)
print(f"件数制限メッセージ: {'あり' if has_limit_msg else 'なし（全件表示）'}")
