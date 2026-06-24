import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import requests
from dotenv import dotenv_values

cfg = dotenv_values("../config/.env")
token = cfg.get("NOTION_API_KEY") or cfg.get("NOTION_TOKEN")

headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

# エンジニアDB と 案件DB 両方のプロパティ名を確認
for label, db_id in [
    ("Engineer", "343450ff-37c0-819d-8769-fb0a8a4ceeb1"),
    ("Project", "343450ff-37c0-81e4-934e-f25f90284a3c"),
]:
    res = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=headers, json={"page_size": 1})
    results = res.json().get("results", [])
    if results:
        keys = list(results[0]["properties"].keys())
        sys.stdout.buffer.write(f"{label} keys:\n".encode("utf-8"))
        for k in keys:
            sys.stdout.buffer.write(f"  {repr(k)}  {k.encode('utf-8').hex()}\n".encode("utf-8"))
