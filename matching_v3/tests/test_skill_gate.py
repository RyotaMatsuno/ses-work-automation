"""skill_gate のユニットテスト。"""

from __future__ import annotations

import sys
from pathlib import Path

MATCHING_V3_DIR = Path(__file__).resolve().parents[1]
if str(MATCHING_V3_DIR) not in sys.path:
    sys.path.insert(0, str(MATCHING_V3_DIR))

from matcher import SkillNormalizer
from skill_gate import (
    classify_skill,
    evaluate_matchability,
    extract_raw_required_skills,
    normalize_technical_skills,
    validate_skill_for_matching,
)


def test_denylist_rejects_task_word():
    assert validate_skill_for_matching("課題")[0] is False
    assert classify_skill("課題") == "TASK_WORDS"


def test_malformed_skill_rejected():
    assert validate_skill_for_matching("Java【必須】")[0] is False


def test_oov_fail_closed_gate():
    case_json = {"extraction_confidence": 0.8}
    extracted = ["WinActor未知語"]
    normalized = []
    matchable, status, _, ng_reason = evaluate_matchability(case_json, extracted, normalized)
    assert matchable is False
    assert status == "UNMATCHABLE_SKILL_OOV"
    assert ng_reason == "ALL_REQUIRED_SKILLS_OOV"


def test_low_quality_gate():
    case_json = {"extraction_confidence": 0.25}
    matchable, status, _, ng_reason = evaluate_matchability(case_json, ["Java"], ["Java"])
    assert matchable is False
    assert status == "UNMATCHABLE_LOW_QUALITY"
    assert ng_reason == "LOW_EXTRACTION_CONFIDENCE"


def test_none_confidence_backward_compatible():
    case_json = {"extraction_confidence": None}
    matchable, status, _, _ = evaluate_matchability(case_json, ["Java"], ["Java"])
    assert matchable is True
    assert status == ""


def test_normalize_technical_skills_filters_denylist():
    normalizer = SkillNormalizer(MATCHING_V3_DIR / "skill_aliases.json")
    case = {"必要スキル": ["課題", "Java"]}
    case_json = {}
    extracted = extract_raw_required_skills(case, case_json)
    technical = normalize_technical_skills(extracted, normalizer)
    assert "課題" not in technical
    assert "Java" in technical


def test_new_aliases_resolve():
    normalizer = SkillNormalizer(MATCHING_V3_DIR / "skill_aliases.json")
    assert normalizer.resolve_canonical("win actor") == "WinActor"
    assert normalizer.resolve_canonical("blueprint") == "Blueprint"
    assert normalizer.resolve_canonical("pc setup") == "PCセットアップ"


def test_denylist_category_punctuation():
    assert classify_skill("△") == "PUNCTUATION"
    assert validate_skill_for_matching("△")[0] is False


def test_denylist_category_email_boilerplate():
    assert classify_skill("いつもお世話") == "EMAIL_BOILERPLATE"


def test_denylist_category_generic_business():
    assert classify_skill("業務委託") == "GENERIC_BUSINESS"


def test_denylist_category_stopwords():
    assert classify_skill("以上") == "STOPWORDS"


def test_rule_deny_single_symbol():
    ok, reason = validate_skill_for_matching("×")
    assert ok is False
    assert reason.startswith("rule_deny:")


def test_rule_deny_email_signature():
    ok, reason = validate_skill_for_matching("株式会社テスト御中")
    assert ok is False
    assert "email_signature" in reason
