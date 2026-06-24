# -*- coding: utf-8 -*-
import io
import sys

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_KEY = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
PROJECT_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"

headers = {"Authorization": f"Bearer {NOTION_KEY}", "Notion-Version": "2022-06-28"}
r = requests.get(f"https://api.notion.com/v1/databases/{PROJECT_DB}", headers=headers)
props = r.json().get("properties", {})
if "入力元" in props:
    print(f"入力元の型: {props['入力元']['type']}")
else:
    print("入力元フィールドが存在しない")
    # 近い名前を探す
    for k in props:
        if "input" in k.lower() or "元" in k or "入力" in k:
            print(f"  候補: {k} -> {props[k]['type']}")
