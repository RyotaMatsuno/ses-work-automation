import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

lw = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
sys.path.insert(0, lw)
os.chdir(lw)
if "line_query" in sys.modules:
    del sys.modules["line_query"]
from line_query import handle_line_query

result = handle_line_query("HS 北小金")
lines = result.split("\n") if result else []

# 「上位」「表示」を含む行を探す
for i, l in enumerate(lines):
    if "上位" in l or "表示" in l:
        print(f"L{i}: {l!r}")
