import importlib
import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query")
import line_query as lq

importlib.reload(lq)

tests = ["HS\u3000北小金", "HS 北小金"]
for t in tests:
    print(f"\n=== {repr(t)} ===")
    result = lq.handle_line_query(t)
    if result:
        # 文字化けしない範囲でprint
        try:
            print(result[:500])
        except:
            print(result.encode("cp932", errors="replace").decode("cp932")[:500])
    else:
        print(repr(result))
