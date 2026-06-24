import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")
from dotenv import dotenv_values

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
API_KEY = cfg.get("NOTION_API_KEY", "")
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

results = []
payload = {"page_size": 100, "filter": {"property": "名前", "title": {"contains": "H.S"}}}
while True:
    r = requests.post(f"https://api.notion.com/v1/databases/{ENG_DB}/query", headers=HEADERS, json=payload, timeout=30)
    data = r.json()
    results.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    payload["start_cursor"] = data["next_cursor"]

print(f"H.S件数: {len(results)}")
for p in results:
    props = p["properties"]
    name = props.get("名前", {}).get("title", [{}])[0].get("plain_text", "")
    owner = props.get("担当者", {}).get("select", {})
    owner_name = owner.get("name", "") if owner else ""
    price = props.get("単価（万円）", {}).get("number", "")
    status = props.get("稼働状況", {}).get("select", {})
    status_name = status.get("name", "") if status else ""
    created = p.get("created_time", "")[:10]
    source = ""
    for k in ["inputSource", "input_source", "InputSource", "入力元"]:
        v = props.get(k, {})
        if v.get("select"):
            source = v["select"].get("name", "")
            break
        if v.get("rich_text"):
            source = "".join(x.get("plain_text", "") for x in v["rich_text"])
            break
    print(
        f"  id={p['id']} name={name} owner={owner_name} price={price} status={status_name} created={created} source={source}"
    )
