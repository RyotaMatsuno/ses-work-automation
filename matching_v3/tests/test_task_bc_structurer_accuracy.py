from __future__ import annotations

import json
from pathlib import Path

import structurer

MATCHING_V3 = Path(__file__).resolve().parents[1]


def test_normalize_budget_around_pattern():
    bmin, bmax = structurer.normalize_budget_from_text("70万前後")
    assert bmin == 67
    assert bmax == 73


def test_normalize_budget_skill_match_is_null():
    assert structurer.normalize_budget_from_text("スキル見合い") == (None, None)


def test_normalize_budget_range_pattern():
    bmin, bmax = structurer.normalize_budget_from_text("80-90万")
    assert bmin == 80
    assert bmax == 90


def test_normalize_budget_upper_only():
    bmin, bmax = structurer.normalize_budget_from_text("〜70万")
    assert bmin is None
    assert bmax == 70


def test_normalize_budget_lower_only():
    bmin, bmax = structurer.normalize_budget_from_text("70万〜")
    assert bmin == 70
    assert bmax is None


def test_normalize_location_tokyo_alias():
    raw, norm = structurer.normalize_location_text("東京都港区六本木")
    assert raw == "東京都港区六本木"
    assert norm == "東京"


def test_normalize_location_remote():
    _, norm = structurer.normalize_location_text("フルリモート可")
    assert norm == "リモート"


def test_apply_strict_schema_maps_v2_fields():
    merged = structurer._apply_strict_schema(
        {
            "must_have_skills": ["Java", "Spring Boot"],
            "nice_to_have_skills": ["AWS"],
            "budget_text": "65〜70万円",
            "location": "東京都港区",
            "remote_type": "hybrid",
            "nationality_ok": False,
        }
    )
    assert "Java" in merged["required_skills"]
    assert "AWS" in merged["optional_skills"]
    assert merged["price_min"] == 65
    assert merged["price_max"] == 70
    assert merged["location_normalized"] == "東京"
    assert merged["remote_ok"] == "partial"
    assert merged["foreign_ok"] is False
    assert merged["field_confidence"]["required_skills"] >= 0.5


def test_representative_case_examples_extract_core_fields():
    """fixtures.json の代表案件でスキル/単価/勤務地が復元できること。"""
    fixtures = json.loads((MATCHING_V3 / "tests" / "fixtures.json").read_text(encoding="utf-8"))
    checked = 0
    examples = fixtures.get("case_examples", [])[:10]
    for item in examples:
        subject = item.get("subject", "")
        body = item.get("body", "")
        expected = item.get("expected", {})
        merged = structurer._postprocess_case_json(expected, subject, body)
        if expected.get("required_skills"):
            assert merged.get("required_skills")
        if expected.get("price_max") is not None:
            assert merged.get("price_max") is not None
        checked += 1
    assert checked == len(examples)
    assert checked >= 5


def test_skill_aliases_reached_250():
    data = json.loads((MATCHING_V3 / "skill_aliases.json").read_text(encoding="utf-8"))
    assert len(data["canonical_skills"]) >= 250
