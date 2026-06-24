from __future__ import annotations

import structurer


def test_split_composite_skills():
    assert structurer._split_composite_skills(["Java/Spring", "MySQL"]) == [
        "Java",
        "Spring",
        "MySQL",
    ]


def test_coerce_price_from_string():
    assert structurer._coerce_price("60万") == 60.0
    assert structurer._coerce_price("650000") == 65.0


def test_compute_extraction_confidence():
    data = {
        "required_skills": ["Java"],
        "price_min": 60.0,
        "work_location": "東京",
        "remote_ok": "none",
    }
    assert structurer._compute_extraction_confidence(data) == 1.0

    sparse = {"required_skills": [], "remote_ok": "unknown"}
    assert structurer._compute_extraction_confidence(sparse) == 0.0


def test_postprocess_splits_and_normalizes_rates():
    raw = {
        "required_skills": ["Java/Spring"],
        "rate_min": "55万",
        "rate_max": "55万",
        "remote_ok": "unknown",
    }
    result = structurer._postprocess_case_json(raw)

    assert "Java" in result["required_skills"]
    assert "Spring" in result["required_skills"]
    assert result["price_min"] == 55.0
    assert result["extraction_confidence"] == 0.5


def test_postprocess_flags_low_confidence():
    raw = {"required_skills": [], "remote_ok": "unknown"}
    result = structurer._postprocess_case_json(raw)

    assert result["extraction_confidence"] == 0.0
    assert result["structure_failed"] is True


def test_subject_fallback_when_required_skills_empty():
    subject = "React+Java 基本設計"
    body = "単価70万"
    raw = {"required_skills": [], "remote_ok": "unknown"}

    result = structurer._postprocess_case_json(raw, subject, body)

    assert "java" in result["required_skills"] or "Java" in result["required_skills"]
    assert result["price_min"] == 70.0
