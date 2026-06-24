"""Task H: ledger daily_state / monthly_state の JST 日付境界テスト."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest


def _freeze_jst(year: int, month: int, day: int, hour: int, minute: int = 0):
    from datetime import timedelta

    jst = timezone(timedelta(hours=9))
    fixed = datetime(year, month, day, hour, minute, tzinfo=jst)

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed.replace(tzinfo=None)
            return fixed.astimezone(tz)

    return _FixedDatetime, fixed


@pytest.mark.parametrize(
    "year,month,day,hour,expected_date",
    [
        (2026, 6, 19, 8, "2026-06-19"),  # JST 08:00 = UTC 前日23:00
        (2026, 6, 19, 0, "2026-06-19"),  # JST 00:30 相当（hour=0）
    ],
)
def test_now_date_uses_jst(isolated_state_dir, year, month, day, hour, expected_date):
    FixedDatetime, _ = _freeze_jst(year, month, day, hour)
    with patch("common.ledger.datetime", FixedDatetime):
        from common.ledger import _now_date, _now_month, record

        assert _now_date() == expected_date
        assert _now_month() == expected_date[:7]

        record(100, 50, "gpt-4o", "test_task_h")

    from common.state_store import open_conn

    conn = open_conn()
    try:
        row = conn.execute("SELECT date FROM daily_state WHERE date=?", (expected_date,)).fetchone()
        assert row is not None
        assert row["date"] == expected_date
    finally:
        conn.close()
