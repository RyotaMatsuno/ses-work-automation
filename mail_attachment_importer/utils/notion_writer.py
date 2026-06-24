"""
notion_writer.py - NotionエンジニアDB upsert（名前+所属で重複判定）
"""

import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from common.notion_register import (
    PROJECT_TITLE_FIELD,
    find_page_by_title,  # noqa: E402
)
from common.notion_register import register_engineer as notion_register_engineer
from common.notion_register import register_project as notion_register_project

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
logger = logging.getLogger(__name__)

NOTION_VERSION = "2022-06-28"

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
]


def _headers():
    return {
        "Authorization": f"Bearer {os.environ['NOTION_API_KEY']}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _engineer_db_id():
    return os.environ.get("NOTION_ENGINEER_DB_ID", "343450ff-37c0-819d-8769-fb0a8a4ceeb1")


def _project_db_id():
    return os.environ.get("NOTION_PROJECT_DB_ID", "343450ff-37c0-81e4-934e-f25f90284a3c")


def _db_id():
    return _engineer_db_id()


def _normalize_skills(skills: list) -> list:
    valid = []
    for skill in skills or []:
        if skill in VALID_SKILLS:
            valid.append(skill)
    return list(dict.fromkeys(valid))


def resolve_affiliation(engineer: dict, meta: dict) -> str:
    """エンジニア情報またはメールメタから所属会社名を解決する。"""
    aff = (engineer.get("affiliation") or "").strip()
    if aff:
        return aff[:200]

    from_addr = meta.get("from", "")
    m = re.search(r"<([^>]+)>", from_addr)
    email = (m.group(1) if m else from_addr).strip()
    domain = email.split("@")[-1] if "@" in email else ""
    if domain and domain not in {"terra-ltd.co.jp", "gmail.com", "yahoo.co.jp"}:
        company = domain.split(".")[0]
        return company[:200]

    account = meta.get("account", "")
    account_map = {
        "sessales": "共通メール",
        "matsuno": "松野メール",
        "okamoto": "岡本メール",
    }
    return account_map.get(account, "")


def _text_prop(page: dict, prop_name: str) -> str:
    prop = page.get("properties", {}).get(prop_name, {})
    if prop.get("type") == "rich_text":
        items = prop.get("rich_text", [])
        return "".join(item.get("plain_text", "") for item in items)
    if prop.get("type") == "title":
        items = prop.get("title", [])
        return "".join(item.get("plain_text", "") for item in items)
    return ""


def find_engineer_page_id(name: str, affiliation: str) -> Optional[str]:
    """名前+所属で既存ページを検索する。"""
    url = f"https://api.notion.com/v1/databases/{_engineer_db_id()}/query"
    payload = {
        "filter": {
            "property": "名前",
            "title": {"equals": name},
        }
    }
    try:
        r = requests.post(url, headers=_headers(), json=payload, timeout=10)
        r.raise_for_status()
        results = r.json().get("results", [])
        if not affiliation:
            return results[0]["id"] if results else None

        aff_norm = affiliation.strip()
        for page in results:
            existing_aff = (_text_prop(page, "所属会社名") or _text_prop(page, "所属会社")).strip()
            if existing_aff == aff_norm:
                return page["id"]
        return None
    except Exception as e:
        logger.error(f"エンジニア検索失敗: {name} / {affiliation} - {e}")
        return None


def check_duplicate(name: str, affiliation: str = "") -> bool:
    """名前+所属の組み合わせが既存ならTrue"""
    return find_engineer_page_id(name, affiliation) is not None


def _build_engineer_properties(engineer: dict, meta: dict) -> dict:
    name = engineer.get("name", "").strip()
    affiliation = resolve_affiliation(engineer, meta)

    properties = {
        "名前": {"title": [{"text": {"content": name}}]},
        "稼働状況": {"select": {"name": "稼働可能"}},
    }

    if affiliation:
        properties["所属会社名"] = {"rich_text": [{"text": {"content": affiliation}}]}
        properties["所属会社"] = {"rich_text": [{"text": {"content": affiliation}}]}

    price = engineer.get("price")
    if price is not None:
        try:
            properties["単価（万円）"] = {"number": float(price)}
        except (TypeError, ValueError):
            pass

    available_date = engineer.get("available_date")
    if available_date:
        try:
            properties["稼働可能日"] = {"date": {"start": available_date}}
        except (TypeError, ValueError):
            pass

    exp = engineer.get("experience_years")
    if exp is not None:
        try:
            properties["経験年数"] = {"number": float(exp)}
        except (TypeError, ValueError):
            pass

    skills = _normalize_skills(engineer.get("skills", []))
    if skills:
        properties["スキル"] = {"multi_select": [{"name": s} for s in skills]}

    account = meta.get("account", "")
    account_label = {"sessales": "共通メール", "matsuno": "松野メール", "okamoto": "岡本メール"}.get(account)
    if account_label:
        properties["入力元"] = {"select": {"name": account_label}}

    memo = f"[自動取込] 件名: {meta.get('subject', '')}\n送信元: {meta.get('from', '')}\n受信日: {meta.get('date', '')}"
    properties["備考（LINEメモ）"] = {"rich_text": [{"text": {"content": memo[:2000]}}]}

    return properties


def upsert_engineer(engineer: dict, meta: dict) -> bool:
    """
    名前+所属でエンジニアDBをupsertする。
    既存があれば更新、なければ新規登録。
    """
    name = engineer.get("name", "").strip()
    if not name:
        logger.warning("氏名なし → スキップ")
        return False

    affiliation = resolve_affiliation(engineer, meta)
    properties = _build_engineer_properties(engineer, meta)
    existing_id = find_engineer_page_id(name, affiliation)

    for attempt in range(2):
        try:
            result = notion_register_engineer(
                properties,
                _engineer_db_id(),
                headers=_headers(),
                existing_page_id=existing_id,
                force_create=existing_id is None,
            )
            if result.get("ok"):
                action = "更新" if result.get("action") == "update" else "新規登録"
                logger.info(f"Notion{action}成功: {name}（所属: {affiliation or '不明'}）")
                return True
            return False
        except Exception as e:
            action = "更新" if existing_id else "新規登録"
            logger.error(f"Notion{action}失敗 (attempt {attempt + 1}): {name} - {e}")
            if attempt == 0:
                time.sleep(2)

    return False


def register_engineer(engineer: dict, meta: dict) -> bool:
    """後方互換エイリアス"""
    return upsert_engineer(engineer, meta)


def check_project_duplicate(name: str) -> bool:
    """案件名で案件DBを検索。存在すればTrue"""
    try:
        found = find_page_by_title(_project_db_id(), PROJECT_TITLE_FIELD, name, headers=_headers())
        if found:
            logger.info(f"案件重複検出: {name} → スキップ")
            return True
        return False
    except Exception as e:
        logger.error(f"案件重複チェック失敗: {name} - {e}")
        return False


def register_project(project: dict, meta: dict) -> bool:
    """案件をNotionプロジェクトDBに登録（案件は名前のみ重複チェック）"""
    name = project.get("name", "").strip()
    if not name:
        logger.warning("案件名なし → スキップ")
        return False

    if check_project_duplicate(name):
        return False

    properties = {
        "案件名": {"title": [{"text": {"content": name}}]},
        "ステータス": {"select": {"name": "募集中"}},
    }

    price = project.get("price")
    if price is not None:
        try:
            properties["単価（万円）"] = {"number": float(price)}
        except (TypeError, ValueError):
            pass

    req_skills = project.get("required_skills", [])
    if req_skills:
        properties["必須スキル"] = {"multi_select": [{"name": s} for s in req_skills]}

    opt_skills = project.get("optional_skills", [])
    if opt_skills:
        properties["尚可スキル"] = {"multi_select": [{"name": s} for s in opt_skills]}

    if project.get("location"):
        properties["勤務地"] = {"rich_text": [{"text": {"content": project["location"]}}]}

    if project.get("period"):
        properties["期間"] = {"rich_text": [{"text": {"content": project["period"]}}]}

    note_parts = []
    if project.get("note"):
        note_parts.append(project["note"])
    if project.get("remote") and project["remote"] != "unknown":
        note_parts.append(f"リモート: {project['remote']}")
    note_parts.append(
        f"[自動取込] 件名: {meta.get('subject', '')}\n送信元: {meta.get('from', '')}\n受信日: {meta.get('date', '')}"
    )
    properties["案件詳細"] = {"rich_text": [{"text": {"content": "\n".join(note_parts)[:2000]}}]}

    for attempt in range(2):
        try:
            result = notion_register_project(properties, _project_db_id(), headers=_headers())
            if result.get("ok"):
                logger.info(f"Notion案件登録成功: {name} ({result.get('action')})")
                return True
            return False
        except Exception as e:
            logger.error(f"Notion案件登録失敗 (attempt {attempt + 1}): {name} - {e}")
            if attempt == 0:
                time.sleep(2)

    return False
