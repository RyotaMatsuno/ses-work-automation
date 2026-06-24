# -*- coding: utf-8 -*-
"""backfill_skills.pyの5件テスト"""

import io
import json
import os
import re
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
from anthropic import Anthropic
from dotenv import dotenv_values

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, "config", ".env")
config = dotenv_values(env_path)
for k, v in config.items():
    if k not in os.environ and v:
        os.environ[k] = v

NOTION_API_KEY = os.environ["NOTION_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
PROJECT_DB_ID = "343450ff-37c0-81e4-934e-f25f90284a3c"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}
MODEL = "claude-haiku-4-5-20251001"
client = Anthropic(api_key=ANTHROPIC_API_KEY)

EXTRACTION_PROMPT = """あなたはSES案件のスキル要件抽出担当です。
以下の案件情報テキストから、必須スキルと尚可スキルを抽出してください。

抽出ルール:
1. プログラミング言語、フレームワーク、ツール、クラウドサービス、DB、OS等の技術スキルのみ抽出
2. 「必須」「MUST」「要件」等の記載の後に続くスキルは必須スキルに分類
3. 「尚可」「あれば望ましい」「WANT」等の記載の後に続くスキルは尚可スキルに分類
4. 明確な区分がない場合は業務内容から推測し、主要技術を必須、補助的なものを尚可に
5. スキル名は短く正規化（例: "Java言語" → "Java", "Amazon Web Services" → "AWS"）
6. 経験年数や業務内容は含めない（技術名のみ）
7. 最大で必須10個、尚可5個まで

必ず以下のJSONのみを返してください:
{"required": ["スキル1", "スキル2"], "optional": ["スキル3"]}""".strip()


def query_all(db_id, filter_obj=None):
    results = []
    payload = {"page_size": 100}
    if filter_obj:
        payload["filter"] = filter_obj
    while True:
        r = requests.post(
            f"https://api.notion.com/v1/databases/{db_id}/query", headers=NOTION_HEADERS, json=payload, timeout=30
        )
        r.raise_for_status()
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return results


def get_body(props):
    parts = []
    for key in ["案件詳細", "備考（LINEメモ）"]:
        rt = props.get(key, {}).get("rich_text", [])
        parts.append("".join(i.get("plain_text", "") for i in rt))
    return " ".join(parts).strip()


def extract_skills_with_ai(body_text):
    truncated = body_text[:2000]
    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        temperature=0,
        system=EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": f"案件情報:\n{truncated}"}],
    )
    text = response.content[0].text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        data = json.loads(match.group(0))
    else:
        data = json.loads(text)
    required = [s.strip() for s in data.get("required", []) if s.strip()][:10]
    optional = [s.strip() for s in data.get("optional", []) if s.strip()][:5]
    return required, optional


# テスト: 5件だけ抽出してNotion更新せず表示
pages = query_all(PROJECT_DB_ID, {"property": "ステータス", "select": {"equals": "募集中"}})
targets = []
for p in pages:
    props = p["properties"]
    skills = [i["name"] for i in props.get("必要スキル", {}).get("multi_select", [])]
    if skills:
        continue
    body = get_body(props)
    if len(body) < 50:
        continue
    name_parts = props.get("案件名", {}).get("title", [])
    name = name_parts[0]["plain_text"] if name_parts else "?"
    targets.append({"id": p["id"], "name": name, "body": body})
    if len(targets) >= 5:
        break

print(f"テスト対象: {len(targets)}件\n")
for t in targets:
    print(f"案件: {t['name']}")
    req, opt = extract_skills_with_ai(t["body"])
    print(f"  必須: {req}")
    print(f"  尚可: {opt}")
    print()
    time.sleep(1.5)
