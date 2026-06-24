import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# line_query モジュールをリロード
import importlib

import line_query

importlib.reload(line_query)

from line_query import _match_initial, _match_station, _normalize_initial, _text_prop

# ダミーエンジニアデータ（H.S / 名前フィールド）
engineer_hs = {
    "properties": {
        "\u540d\u524d": {"title": [{"plain_text": "H.S"}]},
        "\u30a4\u30cb\u30b7\u30e3\u30eb": {"rich_text": []},
        "\u6700\u5bc4\u308a\u99c5": {"rich_text": []},
        "\u5099\u8003\uff08LINE\u30e1\u30e2\uff09": {"rich_text": [{"plain_text": "Registered via mail_pipeline"}]},
    }
}

print("=== normalize test ===")
print("H.S ->", _normalize_initial("H.S"))
print("HS  ->", _normalize_initial("HS"))
print("H S ->", _normalize_initial("H S"))

print("\n=== _match_initial test ===")
result = _match_initial(engineer_hs, "HS")
print("match_initial(H.S, HS):", result)

print("\n=== _match_station test (station not in DB) ===")
result2 = _match_station(engineer_hs, "\u5317\u5c0f\u91d1")
print("match_station(H.S, \u5317\u5c0f\u91d1):", result2)

print("\n=== _text_prop test ===")
ini_val = _text_prop(engineer_hs, "\u30a4\u30cb\u30b7\u30e3\u30eb")
name_val = _text_prop(engineer_hs, "\u540d\u524d")
sta_val = _text_prop(engineer_hs, "\u6700\u5bc4\u308a\u99c5")
print("ini_val:", repr(ini_val))
print("name_val:", repr(name_val))
print("sta_val:", repr(sta_val))
