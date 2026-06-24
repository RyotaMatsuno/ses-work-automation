# -*- coding: utf-8 -*-
"""
エンジニアDBスキル再抽出バッチ
- 「スキル」が空 かつ 「備考（LINEメモ）」テキストがあるエンジニアを対象
- Claude Haiku APIでテキストからスキルを抽出
- Notionのスキルmulti_selectに反映
"""

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
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}
MODEL = "claude-haiku-4-5-20251001"
client = Anthropic(api_key=ANTHROPIC_API_KEY)

LOG_FILE = os.path.join(BASE_DIR, "backfill_eng_skills.log")

EXCLUDE_SKILLS = {
    "excel",
    "word",
    "powerpoint",
    "outlook",
    "teams",
    "コミュニケーション",
    "報告書作成",
    "議事録作成",
}

EXTRACTION_PROMPT = """あなたはSESエンジニアのスキル抽出担当です。
以下のエンジニア情報テキストから保有技術スキルを抽出してください。

抽出ルール:
1. プログラミング言語、フレームワーク、ミドルウェア、クラウドサービス、DB、OS、ツール等の具体的な技術名のみ
2. 件名やサマリーに含まれるスキル名も抽出対象
3. 短く正規化: "Java言語"→"Java", "Amazon Web Services"→"AWS"
4. 業務内容（設計、テスト等）や汎用ツール（Excel等）は除外
5. 最大8個まで
6. テキストにスキル情報がない場合は空配列を返す

JSONのみ返してください: {"skills": ["Java", "Spring"]}""".strip()


def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    print(msg, flush=True)


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


def extract_skills_with_ai(text):
    truncated = text[:1500]
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=300,
                temperature=0,
                system=EXTRACTION_PROMPT,
                messages=[{"role": "user", "content": f"エンジニア情報:\n{truncated}"}],
            )
            resp_text = response.content[0].text.strip()
            match = re.search(r"\{.*\}", resp_text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
            else:
                data = json.loads(resp_text)
            return [s.strip() for s in data.get("skills", []) if s.strip().lower() not in EXCLUDE_SKILLS][:8]
        except Exception:
            if attempt < 2:
                time.sleep(5)
            else:
                return []
    return []


def update_notion_skills(page_id, skills):
    payload = {"properties": {"スキル": {"multi_select": [{"name": s} for s in skills]}}}
    r = requests.patch(f"https://api.notion.com/v1/pages/{page_id}", headers=NOTION_HEADERS, json=payload, timeout=30)
    r.raise_for_status()


def main():
    log("=== エンジニアDBスキル再抽出バッチ開始 ===")

    pages = query_all(ENG_DB, {"property": "稼働状況", "select": {"equals": "稼働可能"}})
    log(f"稼働可能エンジニア: {len(pages)}")

    targets = []
    for p in pages:
        props = p["properties"]
        skills = [i["name"] for i in props.get("スキル", {}).get("multi_select", [])]
        if skills:
            continue

        # 備考（LINEメモ）からテキスト取得
        body = "".join(i.get("plain_text", "") for i in props.get("備考（LINEメモ）", {}).get("rich_text", []))
        if len(body) < 30:
            continue

        name_parts = props.get("名前", {}).get("title", [])
        name = name_parts[0]["plain_text"] if name_parts else "?"
        targets.append({"id": p["id"], "name": name, "body": body})

    log(f"抽出対象: {len(targets)}件")

    success = 0
    fail = 0
    skip = 0

    for i, t in enumerate(targets):
        skills = extract_skills_with_ai(t["body"])
        if not skills:
            log(f"[{i + 1}/{len(targets)}] {t['name']} → スキル抽出なし(skip)")
            skip += 1
            continue

        try:
            update_notion_skills(t["id"], skills)
            log(f"[{i + 1}/{len(targets)}] {t['name']} → {skills}")
            success += 1
        except Exception as e:
            log(f"[{i + 1}/{len(targets)}] {t['name']} → Notion更新失敗: {e}")
            fail += 1

        time.sleep(1.2)

    log(f"=== 完了: 成功={success} 失敗={fail} スキップ={skip} 合計={len(targets)} ===")


if __name__ == "__main__":
    main()
