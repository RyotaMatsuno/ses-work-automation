"""Notion AI作業キュー REST API クライアント."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

from nightly_jobz import config


@dataclass
class QueueTask:
    page_id: str
    task_id: str
    task_type: str
    status: str
    input_data: str
    priority: str = ""


def _headers() -> dict[str, str]:
    api_key = os.environ.get("NOTION_API_KEY", "")
    if not api_key:
        raise RuntimeError("NOTION_API_KEY is not configured")
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": config.NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.request(
        method,
        f"https://api.notion.com/v1/{path}",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Notion API {response.status_code}: {response.text[:300]}")
    return response.json()


def _extract_text(prop: dict[str, Any]) -> str:
    values = prop.get("title") or prop.get("rich_text") or []
    return "".join(item.get("plain_text", "") for item in values)


def _extract_select(prop: dict[str, Any]) -> str:
    return (prop.get("select") or {}).get("name", "")


def parse_task(page: dict[str, Any]) -> QueueTask:
    props = page.get("properties", {})
    return QueueTask(
        page_id=page["id"],
        task_id=_extract_text(props.get("task_id", {})),
        task_type=_extract_select(props.get("種別", {})),
        status=_extract_select(props.get("状態", {})),
        input_data=_extract_text(props.get("入力データ", {})),
        priority=_extract_select(props.get("優先度", {})),
    )


def is_rejected_enqueue(task_type: str, task_id: str) -> bool:
    """push_fail系のdevタスクはキュー汚染防止のため拒否する。"""
    normalized = (task_id or "").strip().lower()
    return task_type == "dev" and normalized.startswith("push_fail")


def fetch_queued_tasks(limit: int = 20) -> list[QueueTask]:
    data = _request(
        "POST",
        f"databases/{config.QUEUE_DB_ID}/query",
        {
            "filter": {
                "or": [
                    {"property": "状態", "select": {"equals": "queued"}},
                    {"property": "状態", "select": {"equals": "running"}},
                ]
            },
            "sorts": [{"timestamp": "created_time", "direction": "ascending"}],
            "page_size": limit,
        },
    )
    tasks = [parse_task(page) for page in data.get("results", [])]
    return [task for task in tasks if not is_rejected_enqueue(task.task_type, task.task_id)]


def update_task_status(
    page_id: str,
    status: str,
    *,
    result_path: str = "",
    dry_run: bool = False,
) -> None:
    properties: dict[str, Any] = {
        "状態": {"select": {"name": status}},
    }
    if status == "done":
        from datetime import datetime, timedelta, timezone

        jst = timezone(timedelta(hours=9))
        properties["完了日時"] = {"date": {"start": datetime.now(jst).date().isoformat()}}
    if result_path.startswith(("http://", "https://")):
        properties["結果リンク"] = {"url": result_path}

    if dry_run:
        return
    _request("PATCH", f"pages/{page_id}", {"properties": properties})
