import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
config = dotenv_values(ROOT / "config" / ".env")
NOTION_API_KEY = config["NOTION_API_KEY"]
WIKI_PAGE_ID = "353450ff-37c0-8145-9e3e-d80c8c8ed594"

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

today = datetime.now().strftime("%Y-%m-%d")


def t(content: str, bold: bool = False) -> dict:
    return {"type": "text", "text": {"content": content}, "annotations": {"bold": bold}}


def para(content: str, bold: bool = False) -> dict:
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [t(content, bold)]}}


def bullet(content: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [t(content)]},
    }


blocks = [
    {"object": "block", "type": "divider", "divider": {}},
    para(f"## {today} matching_v3 ゲート② GO（staleness / 粗利フィルター）", bold=True),
    para("【概要】", bold=True),
    bullet("matching_v3 の鮮度判定バグ修正・粗利フィルター追加・timezone正規化・境界値修正をゲート②で GO 判定"),
    bullet("git commit: f52b5f1 — fix: staleness bug & 粗利フィルター追加 + timezone修正 + 境界値修正 (#gate2-go)"),
    bullet("テスト: test_matcher.py 28 passed"),
    para("【修正内容】", bold=True),
    bullet("is_engineer_fresh(): 最終更新日 / last_updated / _last_edited_time を参照。不明は除外（保守的）"),
    bullet("timezone: datetime.now(timezone.utc) + Zサフィックス replace('Z', '+00:00') 正規化"),
    bullet("境界値: (now - last_updated).days <= 21（microsecond切捨てによる21日ちょうど誤除外を防止）"),
    bullet("粗利: calc_gross_profit() / meets_profit_floor() 追加。松野5万 / 岡本3万"),
    bullet("notion_client.py: 最終更新日プロパティのパース追加"),
    para("【判断マニュアル対応】", bold=True),
    bullet("§2 人材鮮度21日以内 → is_engineer_fresh() + filter_fresh_engineers()"),
    bullet("§4 粗利5万床 → meets_profit_floor() でマッチング前にNG判定"),
]

res = requests.patch(
    f"https://api.notion.com/v1/blocks/{WIKI_PAGE_ID}/children",
    headers=headers,
    json={"children": blocks},
    timeout=30,
)
print(f"status: {res.status_code}")
if res.status_code != 200:
    print(res.text[:300])
else:
    print("Notion Wiki updated OK")
