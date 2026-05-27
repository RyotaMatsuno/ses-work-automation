import sys, io, requests
from dotenv import dotenv_values

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_KEY = cfg["NOTION_API_KEY"]

headers = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

no_name_ids = [
    "365450ff-37c0-81d0-88a0-fd6c9542c410",
    "365450ff-37c0-81c9-a7fa-c9ce174394ad",
    "365450ff-37c0-817c-a716-e9e152d62f2c",
    "365450ff-37c0-8103-bcd2-ddef336ea570",
]

for page_id in no_name_ids:
    # ページ全プロパティ
    r = requests.get(f"https://api.notion.com/v1/pages/{page_id}", headers=headers)
    page = r.json()
    props = page.get("properties", {})
    
    print(f"=== {page_id} ===")
    # 全プロパティ値を出力（空でも）
    for key, val in sorted(props.items()):
        ptype = val.get("type")
        raw = val.get(ptype)
        if raw:
            print(f"  [{ptype}] {key}: {raw}")
    
    # ブロック内容（本文）を確認
    r2 = requests.get(f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=50", headers=headers)
    blocks = r2.json().get("results", [])
    if blocks:
        print(f"  --- ページ本文 ({len(blocks)}ブロック) ---")
        for b in blocks:
            btype = b.get("type", "")
            bdata = b.get(btype, {})
            if isinstance(bdata, dict):
                texts = bdata.get("rich_text", [])
                text = "".join(t.get("plain_text", "") for t in texts)
                if text:
                    print(f"    {text[:200]}")
    print()
