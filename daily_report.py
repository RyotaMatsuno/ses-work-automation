# -*- coding: utf-8 -*-
"""
案件進捗の日次LINE通知。

実行:
  python daily_report.py
  python daily_report.py --dry-run
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from datetime import datetime
from typing import Any

import requests
from dotenv import dotenv_values


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ENV_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
NOTION_API_VERSION = "2022-06-28"
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
LINE_LIMIT = 4900
ACTIVE_STATUSES = ("募集中", "選考中")
WEEKDAYS = ("月", "火", "水", "木", "金", "土", "日")
MATSUNO = "松野"
OKAMOTO = "岡本"
COMMON = "共通"


def load_config() -> dict[str, str]:
    config = dotenv_values(ENV_PATH)
    for key, value in config.items():
        if value is not None and key not in os.environ:
            os.environ[key] = value
    return {key: value or "" for key, value in config.items()}


def require_config(config: dict[str, str], key: str) -> str:
    value = config.get(key) or os.environ.get(key, "")
    if not value:
        raise RuntimeError(f"{key} is not set in {ENV_PATH}")
    return value


def optional_config(config: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = config.get(key) or os.environ.get(key, "")
        if value:
            return value
    return ""


def notion_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json; charset=utf-8",
        "Notion-Version": NOTION_API_VERSION,
    }


def notion_query(database_id: str, api_key: str) -> list[dict[str, Any]]:
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    payload: dict[str, Any] = {
        "page_size": 100,
        "filter": {
            "or": [
                {"property": "ステータス", "select": {"equals": status}}
                for status in ACTIVE_STATUSES
            ]
        },
    }
    results: list[dict[str, Any]] = []

    while True:
        response = requests.post(
            url,
            headers=notion_headers(api_key),
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            return results
        payload["start_cursor"] = data.get("next_cursor")


def plain_text(items: list[dict[str, Any]]) -> str:
    return "".join(item.get("plain_text", "") for item in items).strip()


def property_value(properties: dict[str, Any], name: str) -> Any:
    prop = properties.get(name)
    if not prop:
        return None

    prop_type = prop.get("type")
    if prop_type == "title":
        return plain_text(prop.get("title", []))
    if prop_type == "rich_text":
        return plain_text(prop.get("rich_text", []))
    if prop_type == "select":
        selected = prop.get("select")
        return selected.get("name") if selected else None
    if prop_type == "status":
        status = prop.get("status")
        return status.get("name") if status else None
    if prop_type == "number":
        return prop.get("number")
    if prop_type == "formula":
        formula = prop.get("formula", {})
        return formula.get(formula.get("type"))
    return prop.get(prop_type)


def first_property_value(properties: dict[str, Any], *names: str) -> Any:
    for name in names:
        value = property_value(properties, name)
        if value not in (None, "", []):
            return value
    return None


def as_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def normalize_project(page: dict[str, Any]) -> dict[str, Any]:
    props = page.get("properties", {})
    return {
        "name": property_value(props, "案件名") or "名称未設定",
        "status": property_value(props, "ステータス") or "",
        "price": first_property_value(props, "単価（万円）", "単価(万円)"),
        "assignee": property_value(props, "担当者") or COMMON,
        "proposal": as_int(property_value(props, "提案中")),
        "interview": as_int(property_value(props, "面談希望")),
        "ng": as_int(property_value(props, "NG")),
        "pass": as_int(property_value(props, "合格")),
        "contract": as_int(property_value(props, "成約")),
        "closed": as_int(property_value(props, "営業終了")),
    }


def format_price(value: Any) -> str:
    if value in (None, ""):
        return "-"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def report_header(now: datetime | None = None) -> str:
    current = now or datetime.now()
    weekday = WEEKDAYS[current.weekday()]
    return f"【案件進捗】{current.strftime('%m/%d')}（{weekday}）"


def build_report(projects: list[dict[str, Any]], now: datetime | None = None) -> str:
    lines = [report_header(now), ""]
    if not projects:
        lines.append("本日募集中案件なし")
        return "\n".join(lines)

    action_items: list[str] = []
    # 数字が入っている案件のみ表示（全部0は省略）
    active = [p for p in projects if any(p.get(k, 0) or 0 > 0 for k in ["提案中","面談希望","NG","合格","成約"])]
    display_projects = active if active else []
    for project in display_projects:
        lines.append(f"■ {project['name']}（{format_price(project['price'])}万）")
        status_line = (
            f"  提案中:{project['proposal']} / "
            f"面談希望:{project['interview']} / "
            f"NG:{project['ng']} / "
            f"合格:{project['pass']}"
        )
        extras = []
        if project["contract"] != 0:
            extras.append(f"成約:{project['contract']}")
        if project["closed"] != 0:
            extras.append(f"営業終了:{project['closed']}")
        if extras:
            status_line += " / " + " / ".join(extras)
        lines.append(status_line)
        lines.append("")
        if project["interview"] >= 1:
            action_items.append(f"  {project['name']} → 面談希望{project['interview']}件")

    lines.append("⚡ 要アクション")
    if action_items:
        lines.extend(action_items)
    else:
        lines.append("  なし")
    return "\n".join(lines).rstrip()


def split_line_message(text: str, limit: int = LINE_LIMIT) -> list[str]:
    chunks: list[str] = []
    current = ""
    for line in text.splitlines():
        next_line = line if not current else current + "\n" + line
        if len(next_line) <= limit:
            current = next_line
            continue
        if current:
            chunks.append(current)
        current = line
    if current:
        chunks.append(current)
    return chunks or [text[:limit]]


def push_message(channel_token: str, user_id: str, text: str) -> tuple[int, str]:
    response = requests.post(
        LINE_PUSH_URL,
        headers={
            "Authorization": f"Bearer {channel_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json={"to": user_id, "messages": [{"type": "text", "text": text}]},
        timeout=10,
    )
    return response.status_code, response.text


def projects_for_assignee(
    projects: list[dict[str, Any]],
    assignee: str,
) -> list[dict[str, Any]]:
    return [
        project
        for project in projects
        if project["assignee"] == assignee or project["assignee"] == COMMON
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="案件進捗の日次LINE通知")
    parser.add_argument("--dry-run", action="store_true", help="LINE送信せず出力のみ行う")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()

    notion_api_key = require_config(config, "NOTION_API_KEY")
    project_db_id = require_config(config, "NOTION_PROJECT_DB_ID")

    accounts = {
        MATSUNO: {
            "token": require_config(config, "LINE_CHANNEL_ACCESS_TOKEN"),
            "user_id": require_config(config, "MATSUNO_LINE_USER_ID"),
        },
        OKAMOTO: {
            "token": optional_config(
                config,
                "LINE_OKAMOTO_CHANNEL_ACCESS_TOKEN",
                "OKAMOTO_LINE_CHANNEL_ACCESS_TOKEN",
                "LINE_OKAMOTO_CHANNEL_TOKEN",
            ),
            "user_id": optional_config(config, "OKAMOTO_LINE_USER_ID"),
        },
    }
    if not args.dry_run:
        for assignee, account in accounts.items():
            if not account["token"] or not account["user_id"]:
                raise RuntimeError(f"{assignee} LINE account is not configured")

    pages = notion_query(project_db_id, notion_api_key)
    projects = [normalize_project(page) for page in pages]

    mode = "dry-run" if args.dry_run else "send"
    print(f"[start] mode={mode} active_projects={len(projects)}")

    for assignee, account in accounts.items():
        assignee_projects = projects_for_assignee(projects, assignee)
        report = build_report(assignee_projects)
        chunks = split_line_message(report)

        if args.dry_run:
            print(f"\n--- {assignee} ({len(chunks)}通) ---")
            for index, chunk in enumerate(chunks, 1):
                print(f"[chunk {index}/{len(chunks)} len={len(chunk)}]")
                print(chunk)
            continue

        for chunk in chunks:
            status_code, response_text = push_message(
                account["token"],
                account["user_id"],
                chunk,
            )
            print(f"[sent] to={assignee} status={status_code} response={response_text}")

    print("[done]")


if __name__ == "__main__":
    main()
