from __future__ import annotations

from datetime import datetime, timezone

from matcher import SkillNormalizer, judge_with_meta


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


def test_tier3_only_hits_review():
    case = _case(required_skills=["クラウド"])
    engineer = _fresh_engineer(スキル=["クラウド"])

    result = judge_with_meta(case, engineer, _normalizer())

    assert result["verdict"] == "REVIEW"
    assert result["score_components"]["tier3_count"] >= 1


def test_tier1_and_tier3_can_match():
    case = _case(required_skills=["Java", "クラウド"])
    engineer = _fresh_engineer(スキル=["Java", "クラウド"])

    result = judge_with_meta(case, engineer, _normalizer())

    assert result["verdict"] == "MATCH"
    assert result["score_components"]["exact_count"] >= 2


def test_soft_alias_engineer_skill_partial_match():
    case = _case(required_skills=["Linux"])
    engineer = _fresh_engineer(スキル=["centos"])

    result = judge_with_meta(case, engineer, _normalizer())

    assert result["verdict"] == "PARTIAL_MATCH"
    assert result["score_components"]["soft_alias_count"] == 1


def test_mixed_exact_and_soft_alias_is_match():
    case = _case(required_skills=["Java", "Linux"])
    engineer = _fresh_engineer(スキル=["Java", "centos"])

    result = judge_with_meta(case, engineer, _normalizer())

    assert result["verdict"] == "MATCH"
    assert result["score_components"]["exact_count"] >= 1
    assert result["score_components"]["soft_alias_count"] >= 1


def test_soft_alias_only_partial_match():
    case = _case(required_skills=["c"])
    engineer = _fresh_engineer(スキル=["C言語"])

    result = judge_with_meta(case, engineer, _normalizer())

    assert result["verdict"] == "PARTIAL_MATCH"
    assert result["score_components"]["soft_alias_count"] == 1
