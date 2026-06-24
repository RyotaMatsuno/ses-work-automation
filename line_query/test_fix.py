import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query")
from line_query import classify_query

tests = [
    "HS　北小金",  # 全角スペース
    "HS 北小金",  # 半角スペース
    "HS/北小金",  # スラッシュ
]
for t in tests:
    result = classify_query(t)
    print(f"{repr(t)} -> {result}")
