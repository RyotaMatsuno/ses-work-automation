import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query")

# キャッシュクリア
if "line_query" in sys.modules:
    del sys.modules["line_query"]

import line_query as lq

pages = lq.fetch_all_pages(lq.ENGINEER_DB_ID)

results = []
for p in pages:
    name_raw = lq._text_prop(p, "名前")
    ini_raw = lq._text_prop(p, "イニシャル")
    sta_raw = lq._text_prop(p, "最寄り駅")
    norm = lq._normalize_initial(name_raw) if name_raw else ""
    match_i = lq._match_initial(p, "HS")
    match_s = lq._match_station(p, "北小金")
    if match_i:
        results.append((name_raw, ini_raw, sta_raw, norm, match_i, match_s))

# ファイルに書き出し
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\match_result.txt", "w", encoding="utf-8") as f:
    f.write(f"HS matches: {len(results)}\n")
    for r in results:
        f.write(f"name={r[0]} ini={r[1]} sta={r[2]} norm={r[3]} mi={r[4]} ms={r[5]}\n")

print(f"HS matches: {len(results)}")
print("Written to match_result.txt")
