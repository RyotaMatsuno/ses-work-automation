from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

_MATCHING_RULES_PATH = Path(__file__).resolve().parent.parent / "config" / "matching_rules.json"
JST = ZoneInfo("Asia/Tokyo")


def _load_max_profile_age_days() -> int:
    try:
        with _MATCHING_RULES_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
        return int(data.get("max_profile_age_days", 21))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return 21


STALENESS_DAYS = _load_max_profile_age_days()


def _parse_date_value(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    try:
        if "T" in text:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return parsed.astimezone(JST).date()
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _reference_date(today: date | None) -> date:
    return today or datetime.now(JST).date()


def check(engineer_record: dict, *, today: date | None = None, max_days: int = STALENESS_DAYS) -> dict:
    """
      人材レコードの鮮度を判定する。

    Returns:
          {"is_fresh": bool, "source_field": str, "days_old": int}
          source_field: "情報取得日" | "last_edited_time" | "missing"
    """
    ref = _reference_date(today)

    info_date = _parse_date_value(engineer_record.get("情報取得日"))
    if info_date is not None:
        days_old = (ref - info_date).days
        if days_old < 0:
            return {
                "is_fresh": False,
                "source_field": "情報取得日",
                "days_old": days_old,
            }
        return {
            "is_fresh": days_old <= max_days,
            "source_field": "情報取得日",
            "days_old": days_old,
        }

    last_edited_raw = engineer_record.get("_last_edited_time") or engineer_record.get("last_edited_time")
    last_edited = _parse_date_value(last_edited_raw)
    if last_edited is not None:
        days_old = (ref - last_edited).days
        if days_old < 0:
            return {
                "is_fresh": False,
                "source_field": "last_edited_time",
                "days_old": days_old,
            }
        return {
            "is_fresh": days_old <= max_days,
            "source_field": "last_edited_time",
            "days_old": days_old,
        }

    return {
        "is_fresh": False,
        "source_field": "missing",
        "days_old": -1,
    }


def is_fresh(engineer_record: dict, *, today: date | None = None, max_days: int = STALENESS_DAYS) -> bool:
    return check(engineer_record, today=today, max_days=max_days)["is_fresh"]


def cutoff_date(*, today: date | None = None) -> str:
    """Notion date フィルタ用の on_or_after 値（JST）。"""
    ref = _reference_date(today)
    return (ref - timedelta(days=STALENESS_DAYS)).isoformat()
