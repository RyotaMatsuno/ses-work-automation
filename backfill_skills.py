# -*- coding: utf-8 -*-
"""
案件DBスキル再抽出バッチ（本番用）
593件をバックグラウンドで処理。ログファイルに出力。
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
PROJECT_DB_ID = "343450ff-37c0-81e4-934e-f25f90284a3c"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}
MODEL = "claude-haiku-4-5-20251001"
client = Anthropic(api_key=ANTHROPIC_API_KEY)

LOG_FILE = os.path.join(BASE_DIR, "backfill_skills.log")

# 除外するスキル（汎用的すぎるもの）
EXCLUDE_SKILLS = {
    "excel",
    "word",
    "powerpoint",
    "outlook",
    "teams",
    "運用ドキュメント作成",
    "ドキュメント作成",
    "コミュニケーション",
    "報告書作成",
    "議事録作成",
    "バックエンド開発",
    "フロントエンド開発",
    "システム設計",
    "データベース設計",
    "リファクタリング",
    "要件定義",
    "基本設計",
    "詳細設計",
    "テスト設計",
    "プロジェクト管理",
}

EXTRACTION_PROMPT = """あなたはSES案件のスキル要件抽出担当です。
案件情報テキストから技術スキルのみを抽出してください。

抽出ルール:
1. プログラミング言語、フレームワーク、ミドルウェア、クラウドサービス、DB、OS、ツール等の具体的な技術名のみ
2. 「必須」「MUST」「要件」の後のスキル → required
3. 「尚可」「あれば望ましい」「WANT」の後のスキル → optional
4. 区分不明な場合は主要技術をrequired、補助的なものをoptionalに
5. 短く正規化: "Java言語"→"Java", "Amazon Web Services"→"AWS", ".NET Framework"→".NET"
6. 業務内容（設計、テスト、開発等）や汎用ツール（Excel, Word等）は除外
7. 最大: required 8個、optional 4個

JSONのみ返してください: {"required": ["Java", "Spring"], "optional": ["AWS"]}""".strip()


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


def get_body(props):
    parts = []
    for key in ["案件詳細", "備考（LINEメモ）"]:
        rt = props.get(key, {}).get("rich_text", [])
        parts.append("".join(i.get("plain_text", "") for i in rt))
    return " ".join(parts).strip()


def extract_skills_with_ai(body_text):
    truncated = body_text[:2000]
    for attempt in range(3):
        try:
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

            required = [s.strip() for s in data.get("required", []) if s.strip().lower() not in EXCLUDE_SKILLS][:8]
            optional = [s.strip() for s in data.get("optional", []) if s.strip().lower() not in EXCLUDE_SKILLS][:4]
            return required, optional
        except Exception:
            if attempt < 2:
                time.sleep(5)
            else:
                return [], []
    return [], []


def update_notion_skills(page_id, required_skills, optional_skills):
    payload = {
        "properties": {
            "必要スキル": {"multi_select": [{"name": s} for s in required_skills]},
            "尚可スキル": {"multi_select": [{"name": s} for s in optional_skills]},
        }
    }
    r = requests.patch(f"https://api.notion.com/v1/pages/{page_id}", headers=NOTION_HEADERS, json=payload, timeout=30)
    r.raise_for_status()


def main():
    log("=== 案件DBスキル再抽出バッチ開始 ===")

    pages = query_all(PROJECT_DB_ID, {"property": "ステータス", "select": {"equals": "募集中"}})
    log(f"募集中案件: {len(pages)}")

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

    log(f"抽出対象: {len(targets)}件")

    success = 0
    fail = 0
    skip = 0

    for i, t in enumerate(targets):
        name_short = t["name"][:35]

        required, optional = extract_skills_with_ai(t["body"])
        if not required and not optional:
            log(f"[{i + 1}/{len(targets)}] {name_short} → スキル抽出結果なし(skip)")
            skip += 1
            continue

        try:
            update_notion_skills(t["id"], required, optional)
            log(f"[{i + 1}/{len(targets)}] {name_short} → 必須:{required} 尚可:{optional}")
            success += 1
        except Exception as e:
            log(f"[{i + 1}/{len(targets)}] {name_short} → Notion更新失敗: {e}")
            fail += 1

        time.sleep(1.2)

    log(f"=== 完了: 成功={success} 失敗={fail} スキップ={skip} 合計={len(targets)} ===")


if __name__ == "__main__":
    main()
