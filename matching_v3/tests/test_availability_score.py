from __future__ import annotations

from datetime import date

from matcher import calc_availability_score


def test_availability_immediate():
    assert calc_availability_score(date(2026, 6, 1), date(2026, 6, 15)) == 1.0


def test_availability_within_30_days():
    assert calc_availability_score(date(2026, 7, 10), date(2026, 6, 15)) == 0.8


def test_availability_within_60_days():
    assert calc_availability_score(date(2026, 8, 1), date(2026, 6, 15)) == 0.5


def test_availability_beyond_60_days():
    assert calc_availability_score(date(2026, 10, 1), date(2026, 6, 15)) == 0.2


def test_availability_unknown_is_neutral():
    assert calc_availability_score(None, date(2026, 6, 15)) == 0.5
