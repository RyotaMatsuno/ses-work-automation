from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

import jpholiday
import requests

from config import CASE_DB_ID, ENGINEER_DB_ID, Config
from matcher import ENGINEER_STALENESS_DAYS, filter_fresh_engineers


logger = logging.getLogger(__name__)
JST = timezone(timedelta(hours=9))


class NotionClient:
    BASE_URL = "https://api.notion.com/v1/"
    NOTION_VERSION = "2022-06-28"

    def __init__(self, config: Config | None = None, session: requests.Session | None = None) -> None:
        self.config = config or Config()
        self.session = session or requests.Session()
        self.timeout = 30
        token = self.config.notion_api_key
        if not token:
            raise ValueError("NOTION_API_KEY is required")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": self.NOTION_VERSION,
            "Content-Type": "application/json",
        }

    def get_new_cases(self, days: int) -> list[dict[str, Any]]:
        since = _business_days_ago(days)
        payload = {
            "filter": {
                "and": [
                    {
                        "timestamp": "created_time",
                        "created_time": {"on_or_after": since.isoformat()},
                    },
                ]
            }
        }
        pages = self._query_database(CASE_DB_ID, payload)
        return [self._parse_case_page(page) for page in pages]

    def get_active_engineers(self) -> list[dict[str, Any]]:
        since = (datetime.now(JST) - timedelta(days=ENGINEER_STALENESS_DAYS)).date().isoformat()
        base_filters = [
            {"timestamp": "last_edited_time", "last_edited_time": {"on_or_after": since}},
            {
                "or": [
                    {"property": "稼働状況", "select": {"equals": "稼働可能"}},
                    {"property": "稼働状況", "select": {"equals": "稼働中"}},
                    {"property": "稼働状況", "select": {"equals": "調整中"}},
                ]
            },
        ]
        flag_filter = {"property": "提案対象フラグ", "checkbox": {"equals": True}}
        try:
            pages = self._query_database(
                ENGINEER_DB_ID,
                {"filter": {"and": [flag_filter, *base_filters]}},
            )
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 400:
                logger.warning("提案対象フラグフィルタをスキップしてエンジニア取得: %s", exc)
                pages = self._query_database(ENGINEER_DB_ID, {"filter": {"and": base_filters}})
            else:
                raise
        engineers = [self._parse_engineer_page(page) for page in pages]
        return filter_fresh_engineers(engineers, logger)

    def update_match_status(self, case_id: str, results: list[dict[str, Any]]) -> None:
        try:
            summary = _summarize_results(results)
            # MATCH/REVIEW（提案候補あり）の場合のみ案件ステータスを「選考中」に更新する。
            # NG（候補なし）は案件ステータスを変更しない（募集中のまま維持）。
            # ステータスselectの有効値: 募集中/選考中/成約/終了/稼働中
            if summary in ("MATCH", "REVIEW"):
                self._request(
                    "PATCH",
                    f"pages/{case_id}",
                    json_body={
                        "properties": {
                            "ステータス": {"select": {"name": "選考中"}},
                        }
                    },
                )
        except Exception as exc:
            logger.exception("Notion update_match_status failed: %s", exc)

    def _query_database(self, database_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        next_cursor: str | None = None
        while True:
            body = dict(payload)
            if next_cursor:
                body["start_cursor"] = next_cursor
            data = self._request("POST", f"databases/{database_id}/query", json_body=body)
            results.extend(data.get("results", []))
            next_cursor = data.get("next_cursor")
            if not data.get("has_more") or not next_cursor:
                return results

    def _request(self, method: str, path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = self.BASE_URL + path
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
                if response.status_code < 500:
                    response.raise_for_status()
                    return response.json()
                last_exc = requests.HTTPError(f"{response.status_code}: {response.text}")
            except Exception as exc:
                last_exc = exc
            if attempt < 2:
                time.sleep(delays[attempt])
        if last_exc:
            raise last_exc
        raise RuntimeError("Notion request failed")

    @staticmethod
    def _parse_case_page(page: dict[str, Any]) -> dict[str, Any]:
        props = page.get("properties", {})
        return {
            "id": page.get("id", ""),
            "案件名": _title(props.get("案件名")),
            "案件詳細": _rich_text(props.get("案件詳細")),
            "担当者": _select(props.get("担当者")),
            "_created": _date_value(props.get("登録日時")) or page.get("created_time", ""),
        }

    @staticmethod
    def _parse_engineer_page(page: dict[str, Any]) -> dict[str, Any]:
        props = page.get("properties", {})
        return {
            "id": page.get("id", ""),
            "名前": _title(props.get("名前")),
            "スキル": _multi_select(props.get("スキル")),
            "単価（万円）": _number(props.get("単価（万円）")),
            "経験年数": _number(props.get("経験年数")),
            "稼働状況": _select(props.get("稼働状況")),
            "担当者": _select(props.get("担当者")),
            "備考（LINEメモ）": _rich_text(props.get("備考（LINEメモ）")),
            "最終更新日": _date_value(props.get("最終更新日")),
            "_last_edited_time": page.get("last_edited_time", ""),
        }


def _business_days_ago(days: int) -> date:
    current = datetime.now(JST).date()
    remaining = days
    while remaining > 0:
        current -= timedelta(days=1)
        if current.weekday() < 5 and not jpholiday.is_holiday(current):
            remaining -= 1
    return current


def _summarize_results(results: list[dict[str, Any]]) -> str:
    verdicts = {r.get("verdict") for r in results}
    if "MATCH" in verdicts:
        return "MATCH"
    if "REVIEW" in verdicts:
        return "REVIEW"
    return "NG"


def _title(prop: dict[str, Any] | None) -> str:
    return "".join(item.get("plain_text", "") for item in (prop or {}).get("title", []))


def _rich_text(prop: dict[str, Any] | None) -> str:
    return "".join(item.get("plain_text", "") for item in (prop or {}).get("rich_text", []))


def _multi_select(prop: dict[str, Any] | None) -> list[str]:
    return [item.get("name", "") for item in (prop or {}).get("multi_select", []) if item.get("name")]


def _select(prop: dict[str, Any] | None) -> str | None:
    value = (prop or {}).get("select")
    return value.get("name") if value else None


def _number(prop: dict[str, Any] | None) -> float | None:
    value = (prop or {}).get("number")
    return float(value) if value is not None else None


def _checkbox(prop: dict[str, Any] | None) -> bool:
    return bool((prop or {}).get("checkbox"))


def _date_value(prop: dict[str, Any] | None) -> str | None:
    value = (prop or {}).get("date")
    return value.get("start") if value else None
