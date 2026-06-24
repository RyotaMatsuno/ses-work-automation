import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import importlib

import requests
from dotenv import dotenv_values

import line_query

importlib.reload(line_query)
from line_query import (
    _gross_threshold,
    _multi_select_prop,
    _number_prop,
    _select_prop,
    _text_prop,
    business_days_since,
    calc_gross_profit,
    skill_match,
)

cfg = dotenv_values("../config/.env")
token = cfg.get("NOTION_API_KEY") or cfg.get("NOTION_TOKEN")
headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
PRJ_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"

# H.Sを取得
res = requests.post(f"https://api.notion.com/v1/databases/{ENG_DB}/query", headers=headers, json={"page_size": 50})
engineers = res.json().get("results", [])
hs = next((e for e in engineers if _text_prop(e, "\u540d\u524d") == "H.S"), None)

if not hs:
    sys.stdout.buffer.write(b"H.S not found\n")
    sys.exit(1)

eng_skills = _multi_select_prop(hs, "\u30b9\u30ad\u30eb")
eng_rate = _number_prop(hs, "\u5358\u4fa1\uff08\u4e07\u5186\uff09")
sys.stdout.buffer.write(f"H.S skills: {eng_skills}\n".encode("utf-8"))
sys.stdout.buffer.write(f"H.S rate: {eng_rate}\n".encode("utf-8"))

# 案件を5件サンプルしてフィルタの効き具合を確認
res2 = requests.post(f"https://api.notion.com/v1/databases/{PRJ_DB}/query", headers=headers, json={"page_size": 10})
projects = res2.json().get("results", [])

sys.stdout.buffer.write(b"\nProject filter debug (first 10):\n")
for p in projects:
    name = _text_prop(p, "\u6848\u4ef6\u540d")
    status = _select_prop(p, "\u30b9\u30c6\u30fc\u30bf\u30b9")
    req_sk = _multi_select_prop(p, "\u5fc5\u8981\u30b9\u30ad\u30eb")
    budget = _number_prop(p, "\u5358\u4fa1\uff08\u4e07\u5186\uff09")
    days = business_days_since(p.get("last_edited_time"))
    gross = calc_gross_profit(budget, eng_rate)
    thresh = _gross_threshold(_select_prop(p, "\u62c5\u5f53\u8005"))
    sm = skill_match(req_sk, eng_skills)
    sys.stdout.buffer.write(
        f"  [{status}] {name[:15]} | days={days} | req_sk={req_sk} | sm={sm} | budget={budget} | gross={gross:.1f} >= {thresh}?\n".encode(
            "utf-8"
        )
    )
