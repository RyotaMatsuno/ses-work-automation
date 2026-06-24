import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query")
if "line_query" in sys.modules:
    del sys.modules["line_query"]
import line_query as lq

# engineer_queryを直接呼んで内部状態を確認
pages = lq.fetch_all_pages(lq.ENGINEER_DB_ID)
matched = [p for p in pages if lq._match_initial(p, "HS") and lq._match_station(p, "北小金")]
print(f"matched_engineers: {len(matched)}")
for e in matched:
    print(f"  name={lq._text_prop(e, '名前')}")

# engineer_queryを直接呼ぶ
result = lq.engineer_query("HS", "北小金")
out = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\eng_result.txt"
with open(out, "w", encoding="utf-8") as f:
    f.write(result)
print(f"\nengineer_query result length: {len(result)}")
print(f"First 100 chars: {repr(result[:100])}")
