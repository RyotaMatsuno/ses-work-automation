import io
import re
import sys
from datetime import datetime

import requests
from dotenv import dotenv_values

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

cfg = dotenv_values("config/.env")
NOTION_TOKEN = cfg["NOTION_API_KEY"]
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

today = datetime.now().strftime("%Y-%m-%d")

# 全候補者ステータス付きデータ（全員「意向確認前」）
MATCHING_DATA = [
    ("368450ff-37c0-8137-bf73-e2c9ee1bbc70", [("R.H（24歳・男性）", "48万"), ("AK（男性/60歳）", "70万")]),
    ("368450ff-37c0-81dc-9fa0-de974573ba4f", [("UR", "90万")]),
    ("364450ff-37c0-8173-bcdc-e8d67c5f8f2d", [("R.H（24歳・男性）", "48万"), ("M.H", "55万")]),
    ("364450ff-37c0-81a8-b240-fd79783c92fa", [("M.Y", "65万"), ("KSみずほ台（男性42歳）", "65万"), ("他2名", "")]),
    ("364450ff-37c0-8188-b2fc-e1dd8565ad7d", [("R.E（32歳）", "75万"), ("下溝", "未設定"), ("他4名", "")]),
    ("364450ff-37c0-81e8-8ef9-d8ba1d4f7249", [("M.Y", "65万"), ("KSみずほ台（男性42歳）", "65万"), ("他2名", "")]),
    (
        "364450ff-37c0-815f-b753-dc2daa830733",
        [("R.H（24歳・男性）", "48万"), ("OA（33歳・女性）", "60万"), ("他3名", "")],
    ),
    ("364450ff-37c0-81ef-9c5f-f3da4841d6b1", [("UR", "90万")]),
    ("364450ff-37c0-812a-80a8-d71e796911ac", [("M.Y", "65万")]),
    (
        "364450ff-37c0-811b-ae0e-c4f43246f7a1",
        [("R.H（24歳・男性）", "48万"), ("OA（33歳・女性）", "60万"), ("他2名", "")],
    ),
    (
        "364450ff-37c0-81c6-a402-da286e8e7b1e",
        [("R.H（24歳・男性）", "48万"), ("OA（33歳・女性）", "60万"), ("他1名", "")],
    ),
    (
        "364450ff-37c0-8146-851d-e65b6df2c223",
        [("R.H（24歳・男性）", "48万"), ("OA（33歳・女性）", "60万"), ("他3名", "")],
    ),
    ("360450ff-37c0-812f-baad-e6bb8af73815", [("U.H（33歳・男性）", "45万")]),
    ("35d450ff-37c0-8155-89bd-e23a19af5eb3", [("M.Y", "65万"), ("UR", "90万")]),
    (
        "35d450ff-37c0-810a-bb1c-d02739df3e44",
        [("U.H（33歳・男性）", "45万"), ("R.H（24歳・男性）", "48万"), ("他6名", "")],
    ),
    (
        "35d450ff-37c0-81a6-b954-da27700fe864",
        [("U.H（33歳・男性）", "45万"), ("R.H（24歳・男性）", "48万"), ("他6名", "")],
    ),
    ("344450ff-37c0-8136-bc49-d0f1eb2b44e8", [("R.E（32歳）", "75万"), ("下溝", "未設定"), ("他3名", "")]),
    ("344450ff-37c0-81f8-956f-ed40bfa7c50b", [("OA（33歳・女性）", "60万"), ("M.Y", "65万")]),
    ("344450ff-37c0-81d1-a266-c5465833b391", [("下溝", "未設定"), ("M.Y", "65万"), ("他2名", "")]),
]

STATUS_OPTIONS = ["意向確認前", "意向確認中", "面談希望", "面談調整中", "面談済み", "合格", "NG"]
STATUS_LEGEND = " | ".join(STATUS_OPTIONS)

ok_count = ng_count = 0

for page_id, candidates in MATCHING_DATA:
    # 候補者テキスト生成（ステータス付き）
    lines = [
        f"【候補者ステータス {today}】",
        f"凡例: {STATUS_LEGEND}",
        "",
    ]
    num = 1
    for cname, price in candidates:
        if cname.startswith("他"):
            lines.append(f"  {cname}（Notionで確認）")
        else:
            price_str = price if price else "未設定"
            lines.append(f"  {num}. {cname} /{price_str} ▶ 意向確認前")
            num += 1

    new_block = "\n".join(lines)

    # 既存テキスト取得
    r = requests.get(f"https://api.notion.com/v1/pages/{page_id}", headers=headers, timeout=10)
    if r.status_code != 200:
        print(f"GET NG: {page_id[:8]} {r.status_code}")
        ng_count += 1
        continue

    existing_items = r.json().get("properties", {}).get("案件詳細", {}).get("rich_text", [])
    existing_text = existing_items[0].get("plain_text", "") if existing_items else ""

    # 旧マッチング候補セクションを新ステータスセクションで置換
    if "【候補者ステータス" in existing_text:
        updated = re.sub(r"【候補者ステータス.*", new_block, existing_text, flags=re.DOTALL).strip()
    elif "【マッチング候補" in existing_text:
        updated = re.sub(r"【マッチング候補.*", new_block, existing_text, flags=re.DOTALL).strip()
    else:
        updated = (existing_text + "\n\n" + new_block).strip() if existing_text else new_block

    updated = updated[:1900]

    r2 = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=headers,
        json={"properties": {"案件詳細": {"rich_text": [{"type": "text", "text": {"content": updated}}]}}},
        timeout=10,
    )
    if r2.status_code == 200:
        print(f"OK: {page_id[:8]}", flush=True)
        ok_count += 1
    else:
        print(f"PATCH NG: {page_id[:8]} {r2.status_code}", flush=True)
        ng_count += 1

print(f"\n完了 OK={ok_count} NG={ng_count}")
