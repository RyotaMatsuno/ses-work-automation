import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query")
if "line_query" in sys.modules:
    del sys.modules["line_query"]
import line_query as lq

result = lq.handle_line_query("HS 北小金")
out = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\result_hs.txt"
with open(out, "w", encoding="utf-8") as f:
    f.write(result if result else "(None)")
print(f"Written. Length: {len(result) if result else 0}")
