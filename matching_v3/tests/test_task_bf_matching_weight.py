from __future__ import annotations

from datetime import datetime, timezone

from matcher import (
    GROSS_PROFIT_MAX,
    SkillNormalizer,
    _fuzzy_match,
    calc_match_score_with_breakdown,
    judge_with_meta,
)
from skill_judge import skills_must_not_merge


def _normalizer() -> SkillNormalizer:
    return SkillNormalizer("skill_aliases.json")


def _fresh_engineer(**overrides):
    base = {
        "単価（万円）": 60,
        "_last_edited_time": datetime.now(timezone.utc).isoformat(),
        "スキル": [],
    }
    base.update(overrides)
    return base


def _case(**overrides):
    base = {
        "required_skills": [],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    base.update(overrides)
    return base


def test_required_skill_miss_is_excluded():
    case = _case(required_skills=["Java"], price_max=80)
    engineer = _fresh_engineer(スキル=["Python"])
    engineer["単価（万円）"] = 70

    result = judge_with_meta(case, engineer, _normalizer())

    assert result["verdict"] == "NG"
    assert "必須スキル不足" in result["reasons"][0]


def test_must_have_weight_is_greater_than_nice_to_have():
    must_only, _ = calc_match_score_with_breakdown(
        must_hits=["Java"],
        nice_hits=[],
        price_bonus=False,
        location_bonus=False,
        remote_bonus=False,
    )
    nice_only, _ = calc_match_score_with_breakdown(
        must_hits=[],
        nice_hits=["AWS"],
        price_bonus=False,
        location_bonus=False,
        remote_bonus=False,
    )
    combined, breakdown = calc_match_score_with_breakdown(
        must_hits=["Java"],
        nice_hits=["AWS"],
        price_bonus=False,
        location_bonus=False,
        remote_bonus=False,
    )

    assert must_only > nice_only
    assert breakdown["must_have"]["Java"] > breakdown["nice_to_have"]["AWS"]
    assert combined == must_only + nice_only


def test_java_and_javascript_are_not_merged():
    assert skills_must_not_merge("Java", "JavaScript") is True
    assert skills_must_not_merge("JavaScript", "Java") is True
    assert _fuzzy_match("Java", ["JavaScript"]) is False
    assert _fuzzy_match("JavaScript", ["Java"]) is False


def test_gross_profit_floor_excludes_low_margin():
    case = _case(required_skills=["Java"], price_max=60)
    engineer = _fresh_engineer(スキル=["Java"])
    engineer["単価（万円）"] = 56

    result = judge_with_meta(case, engineer, _normalizer())

    assert result["verdict"] == "NG"
    assert "粗利不足" in result["reasons"][0]


def test_gross_profit_ceiling_excludes_high_margin():
    case = _case(required_skills=["Java"], price_max=90)
    engineer = _fresh_engineer(スキル=["Java"])
    engineer["単価（万円）"] = 70

    result = judge_with_meta(case, engineer, _normalizer())

    assert result["verdict"] == "NG"
    assert "粗利過大" in result["reasons"][0]
    assert 90 - 70 > GROSS_PROFIT_MAX


def test_price_deviation_excludes_expensive_engineer():
    case = _case(required_skills=["Java"], price_max=60)
    engineer = _fresh_engineer(スキル=["Java"])
    engineer["単価（万円）"] = 66

    result = judge_with_meta(case, engineer, _normalizer())

    assert result["verdict"] == "NG"
    assert "粗利不足" in result["reasons"][0]


def test_score_breakdown_is_attached_to_match_result():
    case = _case(
        required_skills=["Java", "Spring"],
        optional_skills=["AWS", "Docker"],
        price_min=70,
        price_max=80,
        work_location="東京",
        remote_ok="partial",
    )
    engineer = _fresh_engineer(
        スキル=["Java", "Spring", "AWS", "Docker"],
        居住地="東京",
        リモート="可",
    )
    engineer["単価（万円）"] = 70

    result = judge_with_meta(case, engineer, _normalizer())

    assert result["verdict"] == "MATCH"
    assert "breakdown" in result
    assert result["breakdown"]["must_have"]["Java"] == 10
    assert result["breakdown"]["must_have"]["Spring"] == 10
    assert result["breakdown"]["nice_to_have"]["AWS"] == 3
    assert result["breakdown"]["nice_to_have"]["Docker"] == 3
    assert result["breakdown"]["price"] == 5
    assert result["breakdown"]["location"] == 3
    assert result["breakdown"]["remote"] == 2
    assert result["total_score"] == 36
