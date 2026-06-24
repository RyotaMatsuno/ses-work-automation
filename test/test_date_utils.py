from datetime import date

import pytest

from common.date_utils import is_active_in_month

TARGET = "2026-07"
FIRST = date(2026, 7, 1)
LAST = date(2026, 7, 31)
NEXT_FIRST = date(2026, 8, 1)
PREV_LAST = date(2026, 6, 30)


@pytest.mark.parametrize(
    "start,end,expected",
    [
        (FIRST, None, True),
        (LAST, None, True),
        (NEXT_FIRST, None, False),
        (FIRST, FIRST, True),
        (FIRST, LAST, True),
        (FIRST, PREV_LAST, False),
        (date(2026, 6, 1), None, True),
        (date(2025, 1, 1), date(2026, 7, 15), True),
        (date(2025, 1, 1), PREV_LAST, False),
    ],
)
def test_is_active_in_month_july_2026(start, end, expected):
    assert is_active_in_month(start, end, TARGET) is expected


def test_december_last_day_calculation():
    assert is_active_in_month(date(2026, 12, 1), None, "2026-12") is True
    assert is_active_in_month(date(2026, 12, 31), None, "2026-12") is True
    assert is_active_in_month(date(2027, 1, 1), None, "2026-12") is False
    assert is_active_in_month(date(2026, 11, 30), date(2026, 12, 31), "2026-12") is True
