import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query")
from line_query import classify_query, handle_line_query

# 全角・半角スペーステスト
tests = ["HS\u3000北小金", "HS 北小金", "HS/北小金"]
for t in tests:
    c = classify_query(t)
    r = handle_line_query(t)
    print(f"INPUT: {repr(t)}")
    print(f"  classify: {c}")
    print(f"  result: {r[:100] if r else repr(r)}")
    print()
