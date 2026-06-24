import sys

# 完全にクリア
for key in list(sys.modules.keys()):
    if "line_query" in key:
        del sys.modules[key]

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query")
# engineer_queryを直接呼ぶ前にパッチ内容確認
import inspect

import line_query as lq

src = inspect.getsource(lq._match_station)
out = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\runtime_source.txt"
with open(out, "w", encoding="utf-8") as f:
    f.write("=== _match_station runtime source ===\n")
    f.write(src)
    f.write("\n\n=== _match_initial runtime source ===\n")
    f.write(inspect.getsource(lq._match_initial))
    f.write("\n\n=== engineer_query runtime source ===\n")
    f.write(inspect.getsource(lq.engineer_query))

# 実行
result = lq.engineer_query("HS", "北小金")
with open(out, "a", encoding="utf-8") as f:
    f.write(f"\n\nResult: {result[:200]}")
print(f"Result: {result[:50]}")
print("Written to runtime_source.txt")
