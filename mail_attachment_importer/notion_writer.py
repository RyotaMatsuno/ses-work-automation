"""
notion_writer.py - Notion登録・重複チェックモジュール
"""
import logging
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
logger = logging.getLogger(__name__)

NOTION_VERSION = "2022-06-28"


def _headers():
    return {
        "Authorization": f"Bearer {os.environ['NOTION_API_KEY']}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _db_id():
    return os.environ.get("NOTION_ENGINEER_DB_ID", "343450ff-37c0-819d-8769-fb0a8a4ceeb1")


def check_duplicate(name: str) -> bool:
    """氏名でエンジニアDBを検索。存在すればTrue"""
    url = f"https://api.notion.com/v1/databases/{_db_id()}/query"
    payload = {
        "filter": {
            "property": "名前",
            "title": {"equals": name}
        }
    }
    try:
        r = requests.post(url, headers=_headers(), json=payload, timeout=10)
        r.raise_for_status()
        results = r.json().get("results", [])
        if results:
            logger.info(f"重複検出: {name} → スキップ")
            return True
        return False
    except Exception as e:
        logger.error(f"重複チェック失敗: {name} - {e}")
        return False


def register_engineer(engineer: dict, meta: dict) -> bool:
    """
    エンジニアをNotionエンジニアDBに登録。

    Args:
        engineer: {"name", "price", "available_date", "experience_years", "skills"}
        meta: {"subject", "from", "date"}  # 元メール情報

    Returns:
        bool: 成功でTrue
    """
    name = engineer.get("name", "").strip()
    if not name:
        logger.warning("氏名なし → スキップ")
        return False

    if check_duplicate(name):
        return False

    # Notionプロパティ構築
    properties = {
        "名前": {"title": [{"text": {"content": name}}]},
        "稼働状況": {"select": {"name": "稼働可能"}},
    }

    price = engineer.get("price")
    if price is not None:
        try:
            properties["単価（万円）"] = {"number": float(price)}
        except Exception:
            pass

    available_date = engineer.get("available_date")
    if available_date:
        try:
            properties["稼働可能日"] = {"date": {"start": available_date}}
        except Exception:
            pass

    exp = engineer.get("experience_years")
    if exp is not None:
        try:
            properties["経験年数"] = {"number": float(exp)}
        except Exception:
            pass

    skills = engineer.get("skills", [])
    if skills:
        properties["スキル"] = {"multi_select": [{"name": s} for s in skills]}

    # 備考: 元メール情報
    memo = f"[自動取込] 件名: {meta.get('subject','')}\n送信元: {meta.get('from','')}\n受信日: {meta.get('date','')}"
    properties["備考（LINEメモ）"] = {"rich_text": [{"text": {"content": memo[:2000]}}]}

    payload = {
        "parent": {"database_id": _db_id()},
        "properties": properties,
    }

    for attempt in range(2):
        try:
            r = requests.post(
                "https://api.notion.com/v1/pages",
                headers=_headers(),
                json=payload,
                timeout=15
            )
            r.raise_for_status()
            logger.info(f"Notion登録成功: {name}")
            return True
        except Exception as e:
            logger.error(f"Notion登録失敗 (attempt {attempt+1}): {name} - {e}")
            if attempt == 0:
                time.sleep(2)

    return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_engineer = {
        "name": "テスト太郎",
        "price": 65,
        "available_date": "2026-06-01",
        "experience_years": 5,
        "skills": ["Java", "Spring", "Oracle"]
    }
    test_meta = {
        "subject": "テスト登録",
        "from": "test@example.com",
        "date": "2026-05-12"
    }
    result = register_engineer(test_engineer, test_meta)
    print(f"登録結果: {result}")
