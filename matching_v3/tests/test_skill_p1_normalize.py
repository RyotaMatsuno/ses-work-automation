"""P1 skill text normalization tests."""

from __future__ import annotations

import sys
from pathlib import Path

MATCHING_V3_DIR = Path(__file__).resolve().parents[1]
if str(MATCHING_V3_DIR) not in sys.path:
    sys.path.insert(0, str(MATCHING_V3_DIR))

from matcher import SkillNormalizer
from skill_gate import (
    evaluate_matchability,
    is_process_skill_name,
    normalize_process_skills,
    normalize_skill_text,
    normalize_technical_skills,
)


def test_p1_category1_experience_suffix():
    assert normalize_skill_text("Java経験") == "Java"
    assert normalize_skill_text("AWS実績") == "AWS"


def test_p1_category2_verb_experience():
    assert normalize_skill_text("Java開発経験") == "Java"
    assert normalize_skill_text("AWS構築経験") == "AWS"


def test_p1_category3_process_experience():
    assert normalize_skill_text("要件定義経験") == "要件定義"
    assert normalize_skill_text("基本設計経験") == "基本設計"
    assert is_process_skill_name("要件定義") is True


def test_p1_low_trust_not_transformed():
    assert normalize_skill_text("Java知識") == "Java知識"
    assert normalize_skill_text("Pythonスキル") == "Pythonスキル"
    assert normalize_skill_text("案件対応可") == "案件対応可"


def test_normalize_technical_skills_applies_p1_before_alias():
    normalizer = SkillNormalizer(MATCHING_V3_DIR / "skill_aliases.json")
    result = normalize_technical_skills(["Java経験", "AWS構築経験"], normalizer)
    assert "Java" in result
    assert "AWS" in result


def test_process_only_required_skills_are_matchable():
    case_json = {"extraction_confidence": 0.9}
    extracted = ["要件定義経験", "基本設計経験"]
    technical = normalize_technical_skills(extracted, SkillNormalizer(MATCHING_V3_DIR / "skill_aliases.json"))
    process = normalize_process_skills(extracted)
    matchable, _, _, ng_reason = evaluate_matchability(case_json, extracted, technical, process)
    assert technical == []
    assert "要件定義" in process
    assert matchable is True
    assert ng_reason == ""


def test_normalize_technical_skills_can_disable_p1():
    normalizer = SkillNormalizer(MATCHING_V3_DIR / "skill_aliases.json")
    with_p1 = normalize_technical_skills(["Java経験"], normalizer, use_p1=True)
    without_p1 = normalize_technical_skills(["Java経験"], normalizer, use_p1=False)
    assert with_p1 == ["Java"]
    assert without_p1 == []
