from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests
from dotenv import dotenv_values

ENV_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
NOTION_API_VERSION = "2022-06-28"
PROJECT_DB_ID = "343450ff-37c0-81e4-934e-f25f90284a3c"
ENGINEER_DB_ID = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"


def load_notion_api_key() -> str:
    config = dotenv_values(ENV_PATH)
    api_key = config.get("NOTION_API_KEY")
    if not api_key:
        raise RuntimeError(f"NOTION_API_KEY is not set in {ENV_PATH}")
    return api_key


def notion_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json; charset=utf-8",
    }


def query_database(
    database_id: str,
    filter_body: dict[str, Any],
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    token = api_key or load_notion_api_key()
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    payload: dict[str, Any] = {"filter": filter_body, "page_size": 100}
    results: list[dict[str, Any]] = []

    while True:
        response = requests.post(
            url,
            headers=notion_headers(token),
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
    if prop_type == "multi_select":
        return [item.get("name", "") for item in prop.get("multi_select", [])]
    if prop_type == "number":
        return prop.get("number")
    if prop_type == "status":
        status = prop.get("status")
        return status.get("name") if status else None
    if prop_type == "people":
        return [person.get("name", "") for person in prop.get("people", [])]
    if prop_type == "formula":
        formula = prop.get("formula", {})
        return formula.get(formula.get("type"))
    if prop_type == "rollup":
        rollup = prop.get("rollup", {})
        return rollup.get(rollup.get("type"))
    if prop_type == "date":
        date_prop = prop.get("date")
        return date_prop.get("start") if date_prop else None
    return prop.get(prop_type)


def first_property_value(properties: dict[str, Any], *names: str) -> Any:
    for name in names:
        value = property_value(properties, name)
        if value not in (None, "", []):
            return value
    return None


def split_skills(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    text = str(value)
    separators = [",", "、", "，", "\n", "/", "／", "・", ";", "；"]
    for separator in separators:
        text = text.replace(separator, ",")
    return [item.strip() for item in text.split(",") if item.strip()]


def parse_created_date(page: dict[str, Any]) -> date | None:
    created_time = page.get("created_time")
    if not created_time:
        return None
    created_time = created_time.replace("Z", "+00:00")
    return datetime.fromisoformat(created_time).astimezone(timezone.utc).date()


def business_days_since(created: date, today: date | None = None) -> int:
    current = created
    end = today or datetime.now(timezone.utc).date()
    days = 0
    while current < end:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days += 1
    return days


def is_recent_project(page: dict[str, Any], today: date | None = None) -> bool:
    created = parse_created_date(page)
    return created is not None and business_days_since(created, today) <= 4


def is_recent_engineer(page: dict[str, Any], today: date | None = None) -> bool:
    created = parse_created_date(page)
    if created is None:
        return False
    end = today or datetime.now(timezone.utc).date()
    return end - created <= timedelta(weeks=3)


def normalize_project(page: dict[str, Any]) -> dict[str, Any]:
    props = page.get("properties", {})
    required_skills = split_skills(property_value(props, "必要スキル"))
    optional_skills = split_skills(property_value(props, "尚可スキル"))
    return {
        "id": page.get("id"),
        "created_time": page.get("created_time"),
        "name": property_value(props, "案件名") or "",
        "required_skills": required_skills,
        "optional_skills": optional_skills,
        "price": first_property_value(props, "単価(万円)", "単価（万円）"),
        "location": property_value(props, "勤務地") or "",
        "period": property_value(props, "期間") or "",
        "detail": property_value(props, "案件詳細") or "",
        "assignee": property_value(props, "担当者") or "",
        "remote": property_value(props, "リモート") or "",
        "interviews": property_value(props, "面談回数") or "",
        "nationality": property_value(props, "外国籍可否") or "",
    }


def normalize_engineer(page: dict[str, Any]) -> dict[str, Any]:
    props = page.get("properties", {})
    return {
        "id": page.get("id"),
        "created_time": page.get("created_time"),
        "name": property_value(props, "名前") or "",
        "skills": split_skills(property_value(props, "スキル")),
        "price": first_property_value(props, "単価(万円)", "単価（万円）"),
        "experience_years": property_value(props, "経験年数"),
        "assignee": property_value(props, "担当者") or "",
        "line_note": first_property_value(props, "備考(LINEメモ)", "備考（LINEメモ）") or "",
        "affiliation": property_value(props, "所属会社") or "",
        "contact_name": property_value(props, "所属担当者名") or "",
        "contact_email": property_value(props, "所属メール") or "",
    }


def fetch_projects(api_key: str | None = None) -> list[dict[str, Any]]:
    filter_body = {"property": "ステータス", "select": {"equals": "募集中"}}
    pages = query_database(PROJECT_DB_ID, filter_body, api_key)
    return [normalize_project(page) for page in pages if is_recent_project(page)]


def fetch_engineers(api_key: str | None = None) -> list[dict[str, Any]]:
    filter_body = {"property": "稼働状況", "select": {"equals": "稼働可能"}}
    pages = query_database(ENGINEER_DB_ID, filter_body, api_key)
    return [normalize_engineer(page) for page in pages if is_recent_engineer(page)]


def main() -> None:
    api_key = load_notion_api_key()
    projects = fetch_projects(api_key)
    engineers = fetch_engineers(api_key)
    print(f"案件数: {len(projects)}")
    print(f"エンジニア数: {len(engineers)}")


if __name__ == "__main__":
    main()
