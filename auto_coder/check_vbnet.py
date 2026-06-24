# -*- coding: utf-8 -*-
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
HEADERS = {
    "Authorization": "Bearer " + (env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")),
    "Notion-Version": "2022-06-28",
}
r = requests.get("https://api.notion.com/v1/pages/380450ff-37c0-81e2-ab77-ed56b56c80a0", headers=HEADERS, timeout=20)
props = r.json().get("properties", {})
for k, v in props.items():
    t = v.get("type")
    val = ""
    if t == "title":
        val = "".join([x.get("plain_text", "") for x in v.get("title", [])])
    elif t == "rich_text":
        val = "".join([x.get("plain_text", "") for x in v.get("rich_text", [])])
    elif t == "select" and v.get("select"):
        val = v["select"].get("name", "")
    elif t == "number" and v.get("number") is not None:
        val = str(v["number"])
    if val:
        print(f"{k}: {val[:300]}")
