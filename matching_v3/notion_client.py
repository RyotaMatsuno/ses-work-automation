from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

import jpholiday
import requests
from matcher import filter_fresh_engineers

from config import CASE_DB_ID, ENGINEER_DB_ID, Config

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

    def get_proposal_target_engineers(self) -> list[dict[str, Any]]:
        """提案対象フラグ=True のエンジニアを全件取得（鮮度フィルタなし）。"""
        flag_filter = {"property": "提案対象フラグ", "checkbox": {"equals": True}}
        try:
            pages = self._query_database(ENGINEER_DB_ID, {"filter": flag_filter})
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 400:
                logger.warning("提案対象フラグフィルタをスキップしてエンジニア取得: %s", exc)
                pages = self._query_database(ENGINEER_DB_ID, {})
            else:
                raise
        return [self._parse_engineer_page(page) for page in pages]

    def update_engineer_unit_price_review(self, page_id: str, memo_text: str) -> bool:
        """単価REVIEW用に提案対象フラグをFalse・備考を更新する。成功=True、400/403/404=False。"""
        properties = {
            "提案対象フラグ": {"checkbox": False},
            "備考（LINEメモ）": {
                "rich_text": [{"type": "text", "text": {"content": memo_text[:2000]}}],
            },
        }
        return self._patch_page_with_rate_limit(page_id, properties)

    def _patch_page_with_rate_limit(self, page_id: str, properties: dict[str, Any]) -> bool:
        url = self.BASE_URL + f"pages/{page_id}"
        delays = [0.5, 1.0, 2.0]
        for attempt in range(3):
            try:
                response = self.session.request(
                    "PATCH",
                    url,
                    headers=self.headers,
                    json={"properties": properties},
                    timeout=self.timeout,
                )
                if response.status_code == 429:
                    if attempt < 2:
                        time.sleep(delays[attempt])
                        continue
                    logger.warning("Notion 429 (rate limit) page_id=%s: %s", page_id, response.text[:200])
                    return False
                if response.status_code in (400, 403, 404):
                    logger.warning(
                        "Notion %s page_id=%s: %s",
                        response.status_code,
                        page_id,
                        response.text[:200],
                    )
                    return False
                response.raise_for_status()
                return True
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status in (400, 403, 404):
                    logger.warning("Notion %s page_id=%s: %s", status, page_id, exc)
                    return False
                if attempt < 2:
                    time.sleep(delays[attempt])
                    continue
                logger.warning("Notion update failed page_id=%s: %s", page_id, exc)
                return False
            except Exception as exc:
                if attempt < 2:
                    time.sleep(delays[attempt])
                    continue
                logger.warning("Notion update failed page_id=%s: %s", page_id, exc)
                return False
        return False

    def get_active_engineers(self) -> list[dict[str, Any]]:
        """提案対象フラグ=True のみで全件取得し、鮮度は Python 側で判定する。"""
        flag_filter = {"property": "提案対象フラグ", "checkbox": {"equals": True}}
        try:
            pages = self._query_database(ENGINEER_DB_ID, {"filter": flag_filter})
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 400:
                logger.error("提案対象フラグフィルタ失敗 - マッチング中断: %s", exc)
                raise RuntimeError(f"提案対象フラグフィルタ利用不可のためマッチング中断: {exc}") from exc
            raise
        engineers = [self._parse_engineer_page(page) for page in pages]
        return filter_fresh_engineers(engineers, logger)

    def get_all_engineers(self) -> list[dict[str, Any]]:
        """エンジニアDB全件取得（鮮度・フラグフィルタなし）。正規化バッチ用。"""
        pages = self._query_database(ENGINEER_DB_ID, {})
        return [self._parse_engineer_page(page) for page in pages]

    def update_engineer_normalized_skills(self, page_id: str, normalized_skills: list[str]) -> bool:
        """正規化スキルフィールドを上書きする。フィールドが存在しない場合は False。"""
        properties = {
            "正規化スキル": {
                "multi_select": [{"name": skill} for skill in normalized_skills],
            }
        }
        return self._patch_page_with_rate_limit(page_id, properties)

    def update_match_status(self, case_id: str, results: list[dict[str, Any]]) -> None:
        try:
            summary = _summarize_results(results)
            properties: dict[str, Any] = {}
            if summary in ("MATCH", "REVIEW"):
                properties["ステータス"] = {"select": {"name": "選考中"}}
            if properties:
                self._request(
                    "PATCH",
                    f"pages/{case_id}",
                    json_body={"properties": properties},
                )
            self.update_matching_status(case_id, "matched" if summary != "NG" else "ng", len(results))
        except Exception as exc:
            logger.exception("Notion update_match_status failed: %s", exc)

    def update_matching_status(
        self,
        case_id: str,
        status: str,
        match_count: int | None = None,
    ) -> bool:
        properties: dict[str, Any] = {
            "matching_status": {"select": {"name": status}},
        }
        if match_count is not None:
            properties["realtime_match_count"] = {"number": match_count}
        return self._patch_page_with_rate_limit(case_id, properties)

    def get_realtime_pending_cases(self, max_hours: float = 3.0) -> list[dict[str, Any]]:
        """matching_status=pending かつ受信から max_hours 以内の案件。"""
        since = datetime.now(JST) - timedelta(hours=max_hours)
        payload = {
            "filter": {
                "and": [
                    {"property": "matching_status", "select": {"equals": "pending"}},
                    {
                        "timestamp": "created_time",
                        "created_time": {"on_or_after": since.isoformat()},
                    },
                ]
            }
        }
        try:
            pages = self._query_database(CASE_DB_ID, payload)
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 400:
                logger.warning("matching_statusフィルタ不可: %s", exc)
                return []
            raise
        return [self._parse_case_page(page) for page in pages]

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
        unit_price = _number(props.get("単価（万円）"))
        purchase_price = _number(props.get("仕入単価（万円）"))
        return {
            "id": page.get("id", ""),
            "案件名": _title(props.get("案件名")),
            "案件詳細": _rich_text(props.get("案件詳細")),
            "案件情報原文": _rich_text(props.get("案件情報原文")),
            "担当者": _select(props.get("担当者")),
            "_created": _date_value(props.get("登録日時")) or page.get("created_time", ""),
            "_last_edited_time": page.get("last_edited_time", ""),
            "created_time": page.get("created_time", ""),
            "必要スキル": _multi_select(props.get("必要スキル")),
            "尚可スキル": _multi_select(props.get("尚可スキル")),
            "単価（万円）": unit_price,
            "単価": unit_price or _number(props.get("単価")),
            "仕入単価（万円）": purchase_price,
            "勤務地": _rich_text(props.get("勤務地")),
            "リモート": _select(props.get("リモート")),
            "年齢制限": _rich_text(props.get("年齢制限")),
            "matching_status": _select(props.get("matching_status")),
            "案件種別": _select(props.get("案件種別")),
        }

    @staticmethod
    def _parse_engineer_page(page: dict[str, Any]) -> dict[str, Any]:
        props = page.get("properties", {})
        return {
            "id": page.get("id", ""),
            "名前": _title(props.get("名前")),
            "スキル": _multi_select(props.get("スキル")),
            "正規化スキル": _multi_select(props.get("正規化スキル")),
            "単価": _number(props.get("単価")),
            "単価（万円）": _engineer_unit_price_man(
                _number(props.get("単価")),
                _number(props.get("単価（万円）")),
            ),
            "経験年数": _number(props.get("経験年数")),
            "稼働状況": _select(props.get("稼働状況")),
            "稼働可能日": _date_value(props.get("稼働可能日")),
            "居住地": _select(props.get("居住地")),
            "担当者": _select(props.get("担当者")),
            "提案対象フラグ": _checkbox(props.get("提案対象フラグ")),
            "備考（LINEメモ）": _rich_text(props.get("備考（LINEメモ）")),
            "国籍": _select(props.get("国籍")),
            "年齢": _number(props.get("年齢")),
            "最終更新日": _date_value(props.get("最終更新日")),
            "情報取得日": _date_value(props.get("情報取得日")),
            "_last_edited_time": page.get("last_edited_time", ""),
        }


def _engineer_unit_price_man(yen_value: float | None, man_value: float | None) -> float | None:
    if man_value is not None:
        return man_value
    if yen_value is not None:
        return yen_value / 10000
    return None


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
    if "PARTIAL_MATCH" in verdicts:
        return "PARTIAL_MATCH"
    if "REVIEW" in verdicts:
        return "REVIEW"
    return "NG"


def realtime_match_window_hours(case: dict[str, Any]) -> float:
    """案件タイマー: 急募2h / 中長期6h / 通常3h。"""
    kind = str(case.get("案件種別") or "").strip()
    name = str(case.get("案件名") or "")
    if kind in ("急募", "urgent") or "急募" in name:
        return 2.0
    if kind in ("中長期", "long_term") or "中長期" in name:
        return 6.0
    return 3.0


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
