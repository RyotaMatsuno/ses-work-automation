from __future__ import annotations

from matcher import calc_experience_score


def test_experience_score_meets_requirement():
    assert calc_experience_score(5, 3) == 1.0


def test_experience_score_one_year_short():
    assert calc_experience_score(2, 3) == 0.7


def test_experience_score_two_years_short():
    assert calc_experience_score(1, 3) == 0.4


def test_experience_score_three_or_more_years_short():
    assert calc_experience_score(0, 3) == 0.1


def test_experience_score_unknown_is_neutral():
    assert calc_experience_score(None, 3) == 0.5
    assert calc_experience_score(5, None) == 0.5
