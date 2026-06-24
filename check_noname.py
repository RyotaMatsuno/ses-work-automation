import io
import sys

import requests
from dotenv import dotenv_values

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_KEY = cfg["NOTION_API_KEY"]

headers = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# 名前が(no name)だった4件のページ詳細を確認
no_name_ids = [
    "365450ff-37c0-81d0-88a0-fd6c9542c410",
    "365450ff-37c0-81c9-a7fa-c9ce174394ad",
    "365450ff-37c0-817c-a716-e9e152d62f2c",
    "365450ff-37c0-8103-bcd2-ddef336ea570",
]

for page_id in no_name_ids:
    r = requests.get(f"https://api.notion.com/v1/pages/{page_id}", headers=headers)
    page = r.json()
    props = page.get("properties", {})
    url = page.get("url", "")

    # 全プロパティを出力
    print(f"=== {page_id} ===")
    print(f"URL: {url}")
    for key, val in props.items():
        ptype = val.get("type")
        if ptype == "title":
            texts = val.get("title", [])
            text = texts[0]["plain_text"] if texts else "(空)"
            print(f"  [{key}] title: '{text}'")
        elif ptype == "rich_text":
            texts = val.get("rich_text", [])
            text = texts[0]["plain_text"] if texts else "(空)"
            if text:
                print(f"  [{key}] rich_text: '{text}'")
        elif ptype == "multi_select":
            items = [s["name"] for s in val.get("multi_select", [])]
            if items:
                print(f"  [{key}] multi_select: {items}")
        elif ptype == "number":
            num = val.get("number")
            if num is not None:
                print(f"  [{key}] number: {num}")
        elif ptype == "select":
            sel = val.get("select")
            if sel:
                print(f"  [{key}] select: '{sel['name']}'")
        elif ptype == "date":
            date_v = val.get("date")
            if date_v:
                print(f"  [{key}] date: {date_v['start']}")

    # ページ内コンテンツ（ブロック）も確認
    r2 = requests.get(f"https://api.notion.com/v1/blocks/{page_id}/children", headers=headers)
    blocks = r2.json().get("results", [])
    if blocks:
        print(f"  --- ページ内コンテンツ ({len(blocks)}ブロック) ---")
        for b in blocks[:5]:
            btype = b.get("type")
            bdata = b.get(btype, {})
            texts = bdata.get("rich_text", [])
            text = texts[0]["plain_text"] if texts else ""
            if text:
                print(f"    [{btype}]: {text[:100]}")
    print()
