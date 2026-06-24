# -*- coding: utf-8 -*-
"""NotionエンジニアDBへの登録・更新処理。"""

import re
from datetime import date

from common.notion_register import register_engineer as notion_register_engineer

NOTION_VERSION = "2022-06-28"
ENGINEER_DB_ID = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

# エンジニアDBに存在するスキルオプション（確認済み）
VALID_SKILLS = [
    "Java",
    "Python",
    "PHP",
    "JavaScript",
    "TypeScript",
    "C#",
    "Node.js",
    "React",
    "AWS",
    "インフラ",
    "PostgreSQL",
    "Oracle",
    "Vue.js",
    "MySQL",
    "Swift",
    "Azure",
    "Linux",
    "Go",
    "Ruby",
    "Docker",
    "MongoDB",
    "Spring",
    "SQL Server",
]

# スキル名の正規化マッピング（よくある表記ゆれ）
SKILL_NORMALIZE = {
    "java": "Java",
    "python": "Python",
    "php": "PHP",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "c#": "C#",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "react": "React",
    "reactjs": "React",
    "aws": "AWS",
    "postgresql": "PostgreSQL",
    "postgre": "PostgreSQL",
    "oracle": "Oracle",
    "vuejs": "Vue.js",
    "vue.js": "Vue.js",
    "vue": "Vue.js",
    "mysql": "MySQL",
    "swift": "Swift",
    "azure": "Azure",
    "linux": "Linux",
    "go": "Go",
    "ruby": "Ruby",
    "docker": "Docker",
    "mongodb": "MongoDB",
    "spring": "Spring",
    "sqlserver": "SQL Server",
    "sql server": "SQL Server",
    "pl/sql": "Oracle",
    "plsql": "Oracle",
    "c++": "C#",  # 近似マッピング（C++はDBにないためC#に寄せず備考行き）
}


def normalize_skills(skills_list: list) -> tuple:
    """
    スキルリストをDBオプションに正規化する。
    Returns: (valid_skills, unknown_skills)
    """
    valid, unknown = [], []
    for s in skills_list or []:
        normalized = SKILL_NORMALIZE.get(s.lower(), s)
        if normalized in VALID_SKILLS:
            valid.append(normalized)
        else:
            unknown.append(s)
    return list(set(valid)), unknown


def source_to_assignee(source: str) -> str:
    if "松野" in source:
        return "松野"
    if "岡本" in source:
        return "岡本"
    return "共通"


def build_properties(record: dict, source: str) -> dict:
    """Notionプロパティ辞書を構築する。"""
    valid_skills, unknown_skills = normalize_skills(record.get("skills_list") or [])
    assignee = source_to_assignee(source)

    props = {
        "名前": {"title": [{"text": {"content": record.get("name") or "（名前不明）"}}]},
        "担当者": {"select": {"name": assignee}},
        "入力元": {"select": {"name": source}},
        "稼働状況": {"select": {"name": "稼働可能"}},
    }

    if valid_skills:
        props["スキル"] = {"multi_select": [{"name": s} for s in valid_skills]}

    if record.get("price"):
        try:
            props["単価（万円）"] = {"number": float(record["price"])}
        except (ValueError, TypeError):
            pass

    if record.get("available_date"):
        try:
            d = str(record["available_date"])[:10]
            date.fromisoformat(d)  # バリデーション
            props["稼働可能日"] = {"date": {"start": d}}
        except (ValueError, TypeError):
            pass

    if record.get("nearest_station"):
        props["最寄り駅"] = {"rich_text": [{"text": {"content": str(record["nearest_station"])[:200]}}]}

    if record.get("affiliation"):
        aff = str(record["affiliation"])[:200]
        props["所属会社名"] = {"rich_text": [{"text": {"content": aff}}]}
        props["所属会社"] = {"rich_text": [{"text": {"content": aff}}]}

    if record.get("experience_years"):
        try:
            props["経験年数"] = {"number": float(record["experience_years"])}
        except (ValueError, TypeError):
            pass

    if record.get("contact_email"):
        props["メール"] = {"email": str(record["contact_email"])}

    if record.get("contact_phone"):
        props["連絡先"] = {"phone_number": str(record["contact_phone"])}

    # イニシャル自動生成
    name = record.get("name") or ""
    m = re.search(r"([A-Z])\.([A-Z])", name)
    if m:
        props["イニシャル"] = {"rich_text": [{"text": {"content": m.group(0)}}]}

    # 人員情報原文
    raw = record.get("raw_text") or ""
    if raw:
        props["人員情報原文"] = {"rich_text": [{"text": {"content": raw[:2000]}}]}

    # 不明スキルを備考に追記
    if unknown_skills:
        note = "【スキル追記】" + ", ".join(unknown_skills)
        props["備考（LINEメモ）"] = {"rich_text": [{"text": {"content": note[:2000]}}]}

    return props


def upsert_engineer(
    record: dict, source: str, file_path: str = None, drive_url: str = None, headers: dict = None, dry_run: bool = False
) -> dict:
    """
    エンジニアDBにレコードを登録または更新する。
    Returns: {"action": "create/update/skip", "page_id": str, "name": str}
    """
    if not headers:
        raise ValueError("notion headers required")

    name = record.get("name")
    if not name:
        return {"action": "skip", "reason": "name is empty"}

    props = build_properties(record, source)

    # ファイルパス / DriveURL
    if file_path:
        props["添付ファイルパス"] = {"rich_text": [{"text": {"content": str(file_path)[:2000]}}]}
    if drive_url:
        props["DriveリンクURL"] = {"url": str(drive_url)}

    result = notion_register_engineer(props, ENGINEER_DB_ID, dry_run=dry_run, headers=headers)
    if result.get("action") == "skip":
        return {"action": "skip", "reason": result.get("reason", "name is empty")}
    if dry_run:
        return {
            "action": "dry_run",
            "name": name,
            "properties": result.get("properties", props),
        }
    return {
        "action": result["action"],
        "page_id": result.get("page_id", ""),
        "name": name,
    }
