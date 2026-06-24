import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import importlib

import requests
from dotenv import dotenv_values

import line_query

importlib.reload(line_query)
from line_query import _prop, _text_prop

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
        props = eng.get("properties", {})
        sys.stdout.buffer.write(b"Props keys: ")
        for k in list(props.keys()):
            sys.stdout.buffer.write(k.encode("utf-8") + b", ")
        sys.stdout.buffer.write(b"\n")

        # _prop で各キーを取得
        for target in ["\u30a4\u30cb\u30b7\u30e3\u30eb", "\u540d\u524d", "\u6700\u5bc4\u308a\u99c5"]:
            p = _prop(eng, target)
            sys.stdout.buffer.write(f"_prop({repr(target)}) -> {repr(p)[:100]}\n".encode("utf-8"))
        break
