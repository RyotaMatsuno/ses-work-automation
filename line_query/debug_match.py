import importlib
import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query")
import line_query as lq

importlib.reload(lq)

pages = lq.fetch_all_pages(lq.ENGINEER_DB_ID)
print(f"Total: {len(pages)}")

for p in pages:
    name = lq._text_prop(p, "名前")
    norm = lq._normalize_initial(name)
    match_ini = lq._match_initial(p, "HS")
    match_sta = lq._match_station(p, "北小金")
    if norm == "HS" or match_ini:
        print(f"name={repr(name)} norm={repr(norm)} match_ini={match_ini} match_sta={match_sta}")
