import sys

for k in list(sys.modules.keys()):
    if "line_query" in k:
        del sys.modules[k]
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query")
import inspect

import line_query as lq

# ランタイムのソースを確認
src = inspect.getsource(lq._match_initial)
# キー文字列のコードポイントを確認
import re

keys = re.findall(r'_text_prop\([^,]+,\s*"([^"]*)"', src)
print("Runtime _match_initial keys:")
for k in keys:
    cps = [f"U+{ord(c):04X}" for c in k]
    print(f"  {repr(k)} = {cps}")

# _match_stationも
src2 = inspect.getsource(lq._match_station)
keys2 = re.findall(r'_text_prop\([^,]+,\s*"([^"]*)"', src2)
print("\nRuntime _match_station keys:")
for k in keys2:
    cps = [f"U+{ord(c):04X}" for c in k]
    print(f"  {repr(k)} = {cps}")

# H.Sに対して実際に何が返るか
pages = lq.fetch_all_pages(lq.ENGINEER_DB_ID)
hs = [p for p in pages if "H.S" in lq._text_prop(p, "\u540d\u524d") or "H.S" == lq._text_prop(p, "\u540d\u524d")]
print(f"\nH.S records: {len(hs)}")
for p in hs:
    name = lq._text_prop(p, "\u540d\u524d")
    ini = lq._text_prop(p, "\u30a4\u30cb\u30b7\u30e3\u30eb")
    sta = lq._text_prop(p, "\u6700\u5bc4\u308a\u99c5")
    mi = lq._match_initial(p, "HS")
    ms = lq._match_station(p, "\u5317\u5c0f\u91d1")
    print(f"  name={name!r} ini={ini!r} sta={sta!r} match_i={mi} match_s={ms}")
