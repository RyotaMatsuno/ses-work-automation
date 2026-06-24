import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query")

# モジュール再ロード
import importlib

import line_query as lq

importlib.reload(lq)

tests = ["HS\u3000北小金", "HS 北小金"]
for t in tests:
    print(f"\n=== {repr(t)} ===")
    result = lq.handle_line_query(t)
    print(result[:300] if result else repr(result))
