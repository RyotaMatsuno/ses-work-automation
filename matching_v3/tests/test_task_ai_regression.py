from __future__ import annotations

from datetime import datetime, timezone

from matcher import SkillNormalizer, _fuzzy_match, judge_with_meta


def _normalizer() -> SkillNormalizer:
    return SkillNormalizer("skill_aliases.json")


def _fresh_engineer(**overrides):
    base = {
        "単価（万円）": 70,
        "_last_edited_time": datetime.now(timezone.utc).isoformat(),
        "スキル": [],
    }
    base.update(overrides)
    return base


def test_strict_fuzzy_alias_no_substring_false_positive():
    normalizer = _normalizer()
    assert not _fuzzy_match("ad", ["Gradle"], strict_keys=normalizer.strict_keys)


def test_strict_fuzzy_alias_exact_match_still_works():
    normalizer = _normalizer()
    assert _fuzzy_match("ad", ["AD"], strict_keys=normalizer.strict_keys)


def test_normalize_short_strict_aliases():
    normalizer = _normalizer()
    assert normalizer.normalize_hard("oci") == "OCI"
    assert normalizer.normalize_hard("bi") == "Power BI"
    assert normalizer.normalize_hard("ad") == "Microsoft Entra ID"


def test_process_requirements_in_judge_meta():
    case = {
        "required_skills": ["Java", "要件定義", "基本設計"],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    engineer = _fresh_engineer(スキル=["Java"])

    result = judge_with_meta(case, engineer, _normalizer())

    assert result["verdict"] == "MATCH"
    assert "要件定義" in result["process_requirements"]
    assert "基本設計" in result["process_requirements"]


def test_parent_child_dedupe_react_and_react_native():
    case = {
        "required_skills": ["React", "React Native"],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    engineer = _fresh_engineer(スキル=["React Native"])

    result = judge_with_meta(case, engineer, _normalizer())

    assert result["verdict"] == "MATCH"


def test_parent_child_rails_satisfies_ruby_requirement():
    case = {"required_skills": ["Ruby"], "price_max": 80, "extraction_confidence": 1.0}
    engineer = _fresh_engineer(スキル=["Rails"])

    result = judge_with_meta(case, engineer, _normalizer())

    assert result["verdict"] == "MATCH"


def test_parent_child_child_does_not_satisfy_parent_only_requirement():
    case = {"required_skills": ["React Native"], "price_max": 80, "extraction_confidence": 1.0}
    engineer = _fresh_engineer(スキル=["React"])

    result = judge_with_meta(case, engineer, _normalizer())

    assert result["verdict"] == "REVIEW"
    assert any("語彙外必須スキル要確認" in reason for reason in result["reasons"])
