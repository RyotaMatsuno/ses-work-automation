from __future__ import annotations

import pytest

from matcher import (
    calc_location_score,
    exact_station_match,
    same_line,
    same_prefecture,
)


def test_exact_station_match():
    assert exact_station_match("新宿駅", "東京都新宿区") is True
    assert exact_station_match("渋谷", "品川") is False


def test_same_line_yamanote():
    assert same_line("渋谷", "新宿") is True
    assert same_line("渋谷", "横浜") is False


def test_same_prefecture():
    assert same_prefecture("渋谷", "池袋") is True
    assert same_prefecture("渋谷", "横浜") is False


def test_calc_location_score_tiers():
    assert calc_location_score("新宿", "新宿") == 1.0
    assert calc_location_score("渋谷", "新宿") == 0.7
    assert calc_location_score("渋谷", "錦糸町") == 0.2
    assert calc_location_score("渋谷", "大阪") == 0.0


def test_calc_location_score_unknown_is_neutral():
    assert calc_location_score(None, "新宿") == 0.0
    assert calc_location_score("新宿", None) == 0.0
