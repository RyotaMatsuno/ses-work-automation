from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import dotenv_values

logger = logging.getLogger(__name__)

ENGINEER_DB_ID = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
NOTION_API_VERSION = "2022-06-28"
RATE_LIMIT_SLEEP = 0.4
BASE_URL = "https://api.notion.com/v1/"

REQUIRED_PROPERTIES: dict[str, dict[str, Any]] = {
    "提案対象フラグ": {"checkbox": {}},
    "除外理由": {"rich_text": {}},
    "国籍": {"select": {}},
    "居住地": {"select": {}},
    "稼働終了日": {"date": {}},
    "短期連続フラグ": {"checkbox": {}},
    "既往歴フラグ": {"checkbox": {}},
}

ENV_PATH = Path(__file__).resolve().parent.parent / "config" / ".env"


class NotionApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class FlagNotionClient:
    def __init__(self, api_key: str | None = None, session: requests.Session | None = None) -> None:
        self.api_key = api_key or _load_notion_api_key()
        if not self.api_key:
            raise ValueError("NOTION_API_KEY is required")
        self.session = session or requests.Session()
        self.timeout = 30
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        }

    def get_database_schema(self, db_id: str) -> dict[str, str]:
        data = self._request("GET", f"databases/{db_id}")
        properties = data.get("properties", {})
        return {name: prop.get("type", "") for name, prop in properties.items()}

    def ensure_properties(self, db_id: str, required_props: dict[str, dict[str, Any]]) -> None:
        schema = self.get_database_schema(db_id)
        missing = {name: definition for name, definition in required_props.items() if name not in schema}
        if not missing:
            logger.info("必要プロパティは全て存在します")
            return
        try:
            self._request("PATCH", f"databases/{db_id}", json_body={"properties": missing})
            logger.info("不足プロパティを追加しました: %s", ", ".join(missing))
        except NotionApiError as exc:
            logger.warning("プロパティ追加に失敗しました。既存スキーマで続行します: %s", exc)

    def get_all_engineers(self, db_id: str) -> list[dict[str, Any]]:
        pages: list[dict[str, Any]] = []
        next_cursor: str | None = None
        while True:
            body: dict[str, Any] = {"page_size": 100}
            if next_cursor:
                body["start_cursor"] = next_cursor
            data = self._request("POST", f"databases/{db_id}/query", json_body=body)
            pages.extend(data.get("results", []))
            if not data.get("has_more"):
                break
            next_cursor = data.get("next_cursor")
        return [self._parse_engineer_page(page) for page in pages]

    def update_engineer_flag(self, page_id: str, flag: bool, reason: str) -> None:
        properties = {
            "提案対象フラグ": {"checkbox": flag},
            "除外理由": {"rich_text": [{"type": "text", "text": {"content": reason[:2000]}}] if reason else []},
        }
        self._request("PATCH", f"pages/{page_id}", json_body={"properties": properties})

    def update_engineer_attributes(
        self,
        page_id: str,
        *,
        nationality: str | None = None,
        residence: str | None = None,
    ) -> None:
        properties: dict[str, Any] = {}
        if nationality:
            properties["国籍"] = {"select": {"name": nationality}}
        if residence:
            properties["居住地"] = {"select": {"name": residence}}
        if not properties:
            return
        self._request("PATCH", f"pages/{page_id}", json_body={"properties": properties})

    def _request(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = BASE_URL + path
        delays = [1, 2, 4]
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                response = self.session.request(
                    method,
                    url,
                    headers=self.headers,
                    json=json_body,
                    timeout=self.timeout,
                )
                if response.status_code == 401:
                    logger.error("Notion API 401: 認証エラー")
                    raise NotionApiError("Notion API authentication failed", 401)
                if response.status_code == 429:
                    last_exc = NotionApiError("Notion API rate limited", 429)
                    if attempt < 2:
                        time.sleep(delays[attempt])
                        continue
                    raise last_exc
                if response.status_code >= 400:
                    raise NotionApiError(
                        f"Notion API {response.status_code}: {response.text[:500]}",
                        response.status_code,
                    )
                return response.json()
            except NotionApiError:
                raise
            except Exception as exc:
                last_exc = exc
                if attempt < 2:
                    time.sleep(delays[attempt])
        if last_exc:
            raise last_exc
        raise RuntimeError("Notion request failed")

    @staticmethod
    def _parse_engineer_page(page: dict[str, Any]) -> dict[str, Any]:
        props = page.get("properties", {})
        return {
            "id": page.get("id", ""),
            "名前": _title(props.get("名前")),
            "備考（LINEメモ）": _rich_text(props.get("備考（LINEメモ）")),
            "properties": {
                "国籍": _select(props.get("国籍")),
                "居住地": _select(props.get("居住地")),
                "稼働終了日": _date_value(props.get("稼働終了日")),
                "短期連続フラグ": _checkbox(props.get("短期連続フラグ")),
                "既往歴フラグ": _checkbox(props.get("既往歴フラグ")),
                "提案対象フラグ": _checkbox(props.get("提案対象フラグ")),
                "除外理由": _rich_text(props.get("除外理由")),
            },
        }


def _load_notion_api_key() -> str | None:
    env = dotenv_values(ENV_PATH, encoding="utf-8")
    return env.get("NOTION_API_KEY")


def _title(prop: dict[str, Any] | None) -> str:
    return "".join(item.get("plain_text", "") for item in (prop or {}).get("title", []))


def _rich_text(prop: dict[str, Any] | None) -> str:
    return "".join(item.get("plain_text", "") for item in (prop or {}).get("rich_text", []))


def _select(prop: dict[str, Any] | None) -> str | None:
    value = (prop or {}).get("select")
    return value.get("name") if value else None


def _checkbox(prop: dict[str, Any] | None) -> bool:
    return bool((prop or {}).get("checkbox"))


def _date_value(prop: dict[str, Any] | None) -> str | None:
    value = (prop or {}).get("date")
    return value.get("start") if value else None
