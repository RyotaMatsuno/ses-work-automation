import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import importlib

import requests
from dotenv import dotenv_values

# line_query を新鮮にインポート
import line_query

importlib.reload(line_query)

from line_query import _match_initial, _match_station, _normalize_initial, _text_prop

cfg = dotenv_values("../config/.env")
token = cfg.get("NOTION_API_KEY") or cfg.get("NOTION_TOKEN")
eng_db = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

# 名前 H.S で検索
res = requests.post(f"https://api.notion.com/v1/databases/{eng_db}/query", headers=headers, json={"page_size": 50})
data = res.json()
results = data.get("results", [])
print(f"Total fetched: {len(results)}")

# 名前フィールド値を確認
PROP_NAME = "\u540d\u524d"
PROP_INI = "\u30a4\u30cb\u30b7\u30e3\u30eb"
PROP_STA = "\u6700\u5bc4\u308a\u99c5"

matched = []
for eng in results:
    name = _text_prop(eng, PROP_NAME)
    ini = _text_prop(eng, PROP_INI)
    sta = _text_prop(eng, PROP_STA)
    norm = _normalize_initial(name)
    if "H" in norm or "HS" in norm:
        print(f"  name={repr(name)} ini={repr(ini)} sta={repr(sta)} norm={repr(norm)}")
    m_ini = _match_initial(eng, "HS")
    m_sta = _match_station(eng, "\u5317\u5c0f\u91d1")
    if m_ini:
        print(f"  -> MATCHED initial! name={repr(name)} sta_match={m_sta}")
        matched.append(eng)

print(f"\nTotal matched (HS): {len(matched)}")
