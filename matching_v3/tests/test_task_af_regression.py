from __future__ import annotations

from datetime import datetime, timezone

from matcher import SkillNormalizer, judge


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


def test_capability_skill_excluded_from_vocab_review():
    case = {
        "required_skills": [
            "Java",
            "ServiceNow",
            "ServiceNow開発経験3年以上",
            "基本設計自走できる人",
            "Azure環境での経験",
        ],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    engineer = _fresh_engineer(スキル=["Java", "ServiceNow"])

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"
    assert not any("語彙外" in reason for reason in reasons)


def test_hard_alias_sql_and_servicenow_match():
    case = {
        "required_skills": ["SQL", "ServiceNow"],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    engineer = _fresh_engineer(スキル=["pl/sql", "servicenow"])

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"
    assert reasons == []


def test_hard_alias_terraform_ci_cd_llm():
    normalizer = _normalizer()
    assert normalizer.normalize_hard("tf") == "Terraform"
    assert normalizer.normalize_hard("ci/cd") == "CI/CD"
    assert normalizer.normalize_hard("LLM") == "生成AI"

    case = {
        "required_skills": ["Terraform", "CI/CD", "生成AI"],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    engineer = _fresh_engineer(スキル=["tf", "ci", "llm"])

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"
    assert reasons == []


def test_soft_alias_does_not_satisfy_required_match():
    case = {"required_skills": ["Ruby"], "price_max": 80, "extraction_confidence": 1.0}
    engineer = _fresh_engineer(スキル=["Python"])

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "NG"
    assert any("必須スキル不足" in reason for reason in reasons)


def test_normalize_hard_ignores_soft_only_aliases():
    normalizer = _normalizer()
    assert normalizer.normalize_hard("centos") is None
    assert normalizer.normalize_soft("centos") == "Linux"
