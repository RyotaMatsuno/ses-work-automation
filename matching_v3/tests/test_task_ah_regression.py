from __future__ import annotations

from datetime import datetime, timezone

from matcher import SkillNormalizer, _fuzzy_match, _normalize_text, judge


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


def test_fuzzy_match_exact_and_partial():
    assert _fuzzy_match("Databricks", ["Databricks", "Python"])
    assert _fuzzy_match("AWS SageMaker", ["SageMaker"])
    assert not _fuzzy_match("Snowflake", ["Java", "Python"])


def test_normalize_text_nfkc():
    assert _normalize_text("ＡＷＳ") == "aws"


def test_match_when_unknown_ratio_below_threshold():
    # Palantir は辞書外スキル（1/11 ≈ 9% < 30% → MATCH）
    case = {
        "required_skills": [
            "Java",
            "Spring",
            "MySQL",
            "AWS",
            "Docker",
            "Linux",
            "Kubernetes",
            "Terraform",
            "Python",
            "Go",
            "Palantir",
        ],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    engineer = _fresh_engineer(
        スキル=["Java", "Spring", "MySQL", "AWS", "Docker", "Linux", "Kubernetes", "tf", "Python", "Go"]
    )

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"
    assert any("語彙外スキル" in reason and "MATCH判定" in reason for reason in reasons)


def test_review_when_unknown_ratio_above_threshold():
    # Palantir / Maximo は辞書外スキル（2/2 = 100% > 30% → REVIEW）
    case = {
        "required_skills": ["Palantir", "Maximo"],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    engineer = _fresh_engineer(スキル=["Java"])

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "REVIEW"
    assert any("語彙外必須スキル要確認" in reason for reason in reasons)


def test_unknown_with_fuzzy_evidence_does_not_count_toward_ratio():
    # Palantir: 辞書外、エンジニアが raw スキルに持つ（fuzzy evidence あり）
    # Maximo: 辞書外、evidence なし
    # Alation: 辞書外、evidence なし
    # unknown_no_evidence = 2/13 ≈ 15% < 30% → MATCH
    case = {
        "required_skills": [
            "Java",
            "Spring",
            "MySQL",
            "AWS",
            "Docker",
            "Linux",
            "Kubernetes",
            "Terraform",
            "Python",
            "Go",
            "Palantir",
            "Maximo",
            "Alation",
        ],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    engineer = _fresh_engineer(
        スキル=["Java", "Spring", "MySQL", "AWS", "Docker", "Linux", "Kubernetes", "tf", "Python", "Go", "Palantir"]
    )

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"
    assert any("語彙外スキル" in reason and "MATCH判定" in reason for reason in reasons)


def test_match_when_only_price_estimate_reasons():
    case = {"required_skills": ["Java"], "price_max": 80, "extraction_confidence": 1.0}
    engineer = _fresh_engineer(スキル=["Java"])
    engineer.pop("単価（万円）")

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"
    assert any(reason.startswith("エンジニア単価推定") for reason in reasons)


def test_ng_unchanged_for_miss_and_gross():
    case = {"required_skills": ["Java"], "price_max": 50, "extraction_confidence": 1.0}
    engineer = _fresh_engineer(スキル=["Python"])
    engineer["単価（万円）"] = 80

    verdict, reasons = judge(case, engineer, _normalizer())
    assert verdict == "NG"
    assert "粗利不足" in reasons[0]

    case2 = {"required_skills": ["Java"], "price_max": 80, "extraction_confidence": 1.0}
    engineer2 = _fresh_engineer(スキル=["Python"])
    verdict2, reasons2 = judge(case2, engineer2, _normalizer())
    assert verdict2 == "NG"
    assert "必須スキル不足" in reasons2[0]
