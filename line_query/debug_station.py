import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import importlib

import requests
from dotenv import dotenv_values

import line_query

importlib.reload(line_query)
from line_query import _match_station, _text_prop

cfg = dotenv_values("../config/.env")
token = cfg.get("NOTION_API_KEY") or cfg.get("NOTION_TOKEN")
eng_db = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

res = requests.post(f"https://api.notion.com/v1/databases/{eng_db}/query", headers=headers, json={"page_size": 50})
results = res.json().get("results", [])

# H.S を探す
PROP_NAME = "\u540d\u524d"
for eng in results:
    name = _text_prop(eng, PROP_NAME)
    if name == "H.S":
        PROP_STA = "\u6700\u5bc4\u308a\u99c5"
        PROP_MEMO = "\u5099\u8003\uff08LINE\u30e1\u30e2\uff09"
        sta = _text_prop(eng, PROP_STA)
        memo = _text_prop(eng, PROP_MEMO)
        station = "\u5317\u5c0f\u91d1"

        sys.stdout.write("sta repr: " + repr(sta) + "\n")
        sys.stdout.write("memo repr: " + repr(memo) + "\n")
        sys.stdout.write("sta is truthy: " + str(bool(sta)) + "\n")
        sys.stdout.write("memo is truthy: " + str(bool(memo)) + "\n")
        sys.stdout.flush()

        # _match_station をステップ実行
        if sta:
            r = station in sta
            sys.stdout.write("branch: sta -> " + str(r) + "\n")
        elif memo:
            r = station in memo
            sys.stdout.write("branch: memo -> " + str(r) + "\n")
        else:
            r = True
            sys.stdout.write("branch: neither -> True\n")

        sys.stdout.write("expected result: " + str(r) + "\n")
        actual = _match_station(eng, station)
        sys.stdout.write("_match_station actual: " + str(actual) + "\n")
        break
