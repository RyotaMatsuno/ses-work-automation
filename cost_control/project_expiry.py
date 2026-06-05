from __future__ import annotations

import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import requests
from dotenv import dotenv_values

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    import jpholiday  # type: ignore
except Exception:
    jpholiday = None


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "config" / ".env"
LOG_PATH = BASE_DIR / "cost_control" / "project_expiry.log"
PROJECT_DB_ID = "343450ff-37c0-81e4-934e-f25f90284a3c"
NOTION_VERSION = "2022-06-28"
OPEN_STATUS = "募集中"
EXPIRED_STATUS = "終了"
PAGE_SIZE = 100
JST = timezone(timedelta(hours=9))

_ENV = dotenv_values(ENV_PATH, encoding="utf-8") if ENV_PATH.exists() else {}
for key, value in _ENV.items():
    if key not in os.environ and value is not None:
        os.environ[key] = value

NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION,
}


def log(message: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def is_business_day(day: date) -> bool:
    if day.weekday() >= 5:
        return False
    if jpholiday is not None:
        return not jpholiday.is_holiday(day)
    return True


def subtract_business_days(start: date, days: int) -> date:
    current = start
    remaining = days
    while remaining > 0:
        current -= timedelta(days=1)
        if is_business_day(current):
            remaining -= 1
    return current


def expiry_created_before(today: date | None = None) -> str:
    base = today or datetime.now().date()
    fourth_business_day_ago = subtract_business_days(base, 4)
    exclusive = datetime.combine(
        fourth_business_day_ago + timedelta(days=1),
        time.min,
        tzinfo=JST,
    )
    return exclusive.isoformat()


def query_expired_projects(created_before: str) -> list[dict]:
    results: list[dict] = []
    payload: dict = {
        "page_size": PAGE_SIZE,
        "filter": {
            "and": [
                {"property": "ステータス", "select": {"equals": OPEN_STATUS}},
                {"timestamp": "created_time", "created_time": {"before": created_before}},
            ]
        },
    }

    while True:
        response = requests.post(
            f"https://api.notion.com/v1/databases/{PROJECT_DB_ID}/query",
            headers=NOTION_HEADERS,
            json=payload,
            timeout=60,
        )
        if response.status_code != 200:
            raise RuntimeError(f"Notion query failed: {response.status_code} {response.text[:300]}")
        data = response.json()
        batch = data.get("results", [])
        results.extend(batch)
        log(f"query page: {len(batch)}件取得 / total={len(results)}")
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data.get("next_cursor")
    return results


def update_project_status(page_id: str) -> None:
    response = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=NOTION_HEADERS,
        json={"properties": {"ステータス": {"select": {"name": EXPIRED_STATUS}}}},
        timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Notion update failed: {response.status_code} {response.text[:300]}")


def main() -> int:
    if not NOTION_API_KEY:
        log("NOTION_API_KEY未設定のため終了")
        return 1

    created_before = expiry_created_before()
    log(f"案件自動失効開始: DB={PROJECT_DB_ID} status={OPEN_STATUS} created_before={created_before}")
    pages = query_expired_projects(created_before)
    log(f"更新対象: {len(pages)}件")

    updated = 0
    for page in pages:
        page_id = page.get("id", "")
        created_time = page.get("created_time", "")
        if not page_id:
            continue
        update_project_status(page_id)
        updated += 1
        log(f"updated: {page_id} created_time={created_time}")

    log(f"案件自動失効完了: updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
