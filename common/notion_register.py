from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import dotenv_values

logger = logging.getLogger(__name__)

NOTION_VERSION = "2022-06-28"
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "config" / ".env"
_ENV = dotenv_values(ENV_PATH, encoding="utf-8") if ENV_PATH.exists() else {}

ENGINEER_TITLE_FIELD = "名前"
PROJECT_TITLE_FIELD = "案件名"
PROJECT_SOURCE_FIELD = "入力元"

_IMMEDIATE_ERROR_STATUSES = {400, 401, 404}


class NotionAPIError(Exception):
    def __init__(self, status: int, body: str) -> None:
        self.status = status
        self.body = body
        super().__init__(f"Notion API error {status}: {body[:300]}")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name) or _ENV.get(name) or default


def notion_headers() -> dict[str, str]:
    token = _env("NOTION_API_KEY")
    if not token:
        raise ValueError("NOTION_API_KEY is required")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _extract_title(page_properties: dict[str, Any], title_field: str) -> str | None:
    prop = page_properties.get(title_field) or {}
    items = prop.get("title") or []
    if not items:
        return None
    content = str(items[0].get("text", {}).get("content", "")).strip()
    return content or None


def _extract_select_source(page_properties: dict[str, Any]) -> str | None:
    prop = page_properties.get(PROJECT_SOURCE_FIELD) or {}
    name = prop.get("select", {}).get("name", "")
    name = str(name).strip()
    return name or None


def _search_page_by_title(
    db_id: str,
    title_field: str,
    title_value: str,
    headers: dict[str, str],
) -> str | None:
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    payload = {
        "filter": {
            "property": title_field,
            "title": {"equals": title_value},
        }
    }
    resp = _request_with_retry("POST", url, headers, payload)
    results = resp.json().get("results", [])
    return results[0]["id"] if results else None


def _search_page_by_title_and_source(
    db_id: str,
    title_field: str,
    title_value: str,
    source_value: str,
    headers: dict[str, str],
) -> str | None:
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    payload = {
        "filter": {
            "and": [
                {
                    "property": title_field,
                    "title": {"equals": title_value},
                },
                {
                    "property": PROJECT_SOURCE_FIELD,
                    "select": {"equals": source_value},
                },
            ]
        }
    }
    resp = _request_with_retry("POST", url, headers, payload)
    results = resp.json().get("results", [])
    return results[0]["id"] if results else None


def _should_retry(status_code: int) -> bool:
    return status_code == 429 or status_code >= 500


def _request_with_retry(
    method: str,
    url: str,
    headers: dict[str, str],
    json_body: dict[str, Any] | None = None,
) -> requests.Response:
    delays = [1, 2]
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = requests.request(method, url, headers=headers, json=json_body, timeout=30)
            if resp.status_code in _IMMEDIATE_ERROR_STATUSES:
                raise NotionAPIError(resp.status_code, resp.text)
            if _should_retry(resp.status_code):
                last_exc = NotionAPIError(resp.status_code, resp.text)
            elif resp.status_code >= 400:
                raise NotionAPIError(resp.status_code, resp.text)
            else:
                return resp
        except NotionAPIError as exc:
            if not _should_retry(exc.status):
                raise
            last_exc = exc
        except requests.RequestException as exc:
            last_exc = exc
        if attempt < 2:
            time.sleep(delays[min(attempt, len(delays) - 1)])
    if last_exc:
        raise last_exc
    raise RuntimeError("Notion request failed")


def _upsert_page(
    page_properties: dict[str, Any],
    db_id: str,
    title_field: str,
    *,
    dry_run: bool = False,
    headers: dict[str, str] | None = None,
    existing_page_id: str | None = None,
    force_create: bool = False,
) -> dict[str, Any]:
    hdrs = headers or notion_headers()
    title = _extract_title(page_properties, title_field)
    if not title:
        return {"action": "skip", "ok": False, "reason": "title is empty", "page_id": ""}

    if dry_run:
        return {
            "action": "dry_run",
            "ok": True,
            "page_id": existing_page_id or "",
            "title": title,
            "properties": page_properties,
        }

    if existing_page_id:
        resolved_id = existing_page_id
    elif force_create:
        resolved_id = None
    else:
        resolved_id = _search_page_by_title(db_id, title_field, title, hdrs)

    if resolved_id:
        _request_with_retry(
            "PATCH",
            f"https://api.notion.com/v1/pages/{resolved_id}",
            hdrs,
            {"properties": page_properties},
        )
        logger.info("Notion update: %s (%s)", title, resolved_id)
        return {"action": "update", "ok": True, "page_id": resolved_id, "title": title}

    resp = _request_with_retry(
        "POST",
        "https://api.notion.com/v1/pages",
        hdrs,
        {"parent": {"database_id": db_id}, "properties": page_properties},
    )
    page_id = resp.json().get("id", "")
    logger.info("Notion create: %s (%s)", title, page_id)
    return {"action": "create", "ok": True, "page_id": page_id, "title": title}


def find_page_by_title(
    db_id: str,
    title_field: str,
    title_value: str,
    *,
    headers: dict[str, str] | None = None,
) -> str | None:
    """タイトルフィールドで既存ページIDを検索する。"""
    return _search_page_by_title(db_id, title_field, title_value, headers or notion_headers())


def find_page_by_title_and_source(
    db_id: str,
    title_field: str,
    title_value: str,
    source_value: str,
    *,
    headers: dict[str, str] | None = None,
) -> str | None:
    """案件名+入力元の複合キーで既存ページIDを検索する。"""
    return _search_page_by_title_and_source(
        db_id,
        title_field,
        title_value,
        source_value,
        headers or notion_headers(),
    )


def register_engineer(
    page_properties: dict[str, Any],
    db_id: str,
    dry_run: bool = False,
    *,
    headers: dict[str, str] | None = None,
    existing_page_id: str | None = None,
    force_create: bool = False,
) -> dict[str, Any]:
    """エンジニアDBへ登録または更新（名前タイトルで重複チェック→upsert）。"""
    return _upsert_page(
        page_properties,
        db_id,
        ENGINEER_TITLE_FIELD,
        dry_run=dry_run,
        headers=headers,
        existing_page_id=existing_page_id,
        force_create=force_create,
    )


def register_project(
    page_properties: dict[str, Any],
    db_id: str,
    dry_run: bool = False,
    *,
    headers: dict[str, str] | None = None,
    existing_page_id: str | None = None,
    force_create: bool = False,
) -> dict[str, Any]:
    """案件DBへ登録または更新（案件名+入力元で重複チェック→upsert）。"""
    hdrs = headers or notion_headers()
    title = _extract_title(page_properties, PROJECT_TITLE_FIELD)
    if not title:
        return {"action": "skip", "ok": False, "reason": "title is empty", "page_id": ""}

    source = _extract_select_source(page_properties)
    effective_force_create = force_create or source is None

    if dry_run:
        return {
            "action": "dry_run",
            "ok": True,
            "page_id": existing_page_id or "",
            "title": title,
            "properties": page_properties,
        }

    if existing_page_id:
        resolved_id = existing_page_id
    elif effective_force_create:
        resolved_id = None
    else:
        resolved_id = _search_page_by_title_and_source(db_id, PROJECT_TITLE_FIELD, title, source, hdrs)

    if resolved_id:
        _request_with_retry(
            "PATCH",
            f"https://api.notion.com/v1/pages/{resolved_id}",
            hdrs,
            {"properties": page_properties},
        )
        logger.info("Notion update: %s / %s (%s)", title, source, resolved_id)
        return {"action": "update", "ok": True, "page_id": resolved_id, "title": title}

    resp = _request_with_retry(
        "POST",
        "https://api.notion.com/v1/pages",
        hdrs,
        {"parent": {"database_id": db_id}, "properties": page_properties},
    )
    page_id = resp.json().get("id", "")
    logger.info("Notion create: %s / %s (%s)", title, source or "(no source)", page_id)
    return {"action": "create", "ok": True, "page_id": page_id, "title": title}
