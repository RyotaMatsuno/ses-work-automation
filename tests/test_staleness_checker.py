from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "matching_v3"))

from staleness_checker import STALENESS_DAYS, check


def _today() -> date:
    return date(2026, 6, 10)


def test_fresh_by_info_acquired_date_20_days():
    result = check(
        {"情報取得日": (_today() - timedelta(days=20)).isoformat()},
        today=_today(),
    )

    assert result == {
        "is_fresh": True,
        "source_field": "情報取得日",
        "days_old": 20,
    }


def test_fresh_boundary_21_days_by_info_acquired_date():
    result = check(
        {"情報取得日": (_today() - timedelta(days=STALENESS_DAYS)).isoformat()},
        today=_today(),
    )

    assert result["is_fresh"] is True
    assert result["source_field"] == "情報取得日"
    assert result["days_old"] == 21


def test_stale_boundary_22_days_by_info_acquired_date():
    result = check(
        {"情報取得日": (_today() - timedelta(days=STALENESS_DAYS + 1)).isoformat()},
        today=_today(),
    )

    assert result["is_fresh"] is False
    assert result["source_field"] == "情報取得日"
    assert result["days_old"] == 22


def test_future_info_acquired_date_is_not_fresh():
    result = check(
        {"情報取得日": (_today() + timedelta(days=1)).isoformat()},
        today=_today(),
    )

    assert result["is_fresh"] is False
    assert result["source_field"] == "情報取得日"
    assert result["days_old"] < 0


def test_fallback_to_last_edited_time_when_info_missing():
    result = check({"_last_edited_time": "2026-05-21T12:00:00+00:00"}, today=_today())

    assert result["is_fresh"] is True
    assert result["source_field"] == "last_edited_time"
    assert result["days_old"] == 20


def test_stale_by_last_edited_time_when_info_missing():
    result = check({"_last_edited_time": "2026-05-19T12:00:00+00:00"}, today=_today())

    assert result["is_fresh"] is False
    assert result["source_field"] == "last_edited_time"
    assert result["days_old"] == 22


def test_prefers_info_acquired_date_over_last_edited_time():
    result = check(
        {
            "情報取得日": (_today() - timedelta(days=5)).isoformat(),
            "_last_edited_time": "2026-05-01T12:00:00+00:00",
        },
        today=_today(),
    )

    assert result["source_field"] == "情報取得日"
    assert result["is_fresh"] is True


def test_missing_both_fields():
    result = check({"名前": "テスト"}, today=_today())

    assert result == {
        "is_fresh": False,
        "source_field": "missing",
        "days_old": -1,
    }
