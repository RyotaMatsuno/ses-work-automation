from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import structurer
from common.email_cleaner import clean_email_body
from common.normalizers import normalize_availability, normalize_rate, normalize_rate_fields
from matcher import SkillNormalizer, judge_with_meta
from processed_db import ProcessedDB


def test_remove_signature():
    body = "案件内容\n必須Java\n--\n山田太郎\nTEL:03-1234-5678"
    cleaned = clean_email_body(body)
    assert "TEL" not in cleaned
    assert "Java" in cleaned


def test_remove_disclaimer():
    body = "案件詳細\n本メールは送信専用です。返信できません。"
    cleaned = clean_email_body(body)
    assert "送信専用" not in cleaned
    assert "案件詳細" in cleaned


def test_remove_quoted_reply():
    body = "新規案件\n> 前回の引用\nOn Mon wrote:"
    cleaned = clean_email_body(body)
    assert "新規案件" in cleaned
    assert "引用" not in cleaned


def test_normalize_rate_patterns():
    assert normalize_rate("70万") == (70.0, 70.0)
    assert normalize_rate("70-75万") == (70.0, 75.0)
    assert normalize_rate("〜80万") == (None, 80.0)
    assert normalize_rate("700000") == (70.0, 70.0)
    assert normalize_rate("スキル見合い") == (None, None)


def test_normalize_rate_fields_swaps_inverted_range():
    pmin, pmax, warnings = normalize_rate_fields(80, 60)
    assert pmin == 60.0
    assert pmax == 80.0
    assert warnings


def test_normalize_availability():
    assert normalize_availability("即日") == "即日"
    assert normalize_availability("来月", today=date(2026, 6, 15)) == "2026-07"
    assert normalize_availability("7月〜", today=date(2026, 6, 15)) == "2026-07"


def test_required_completeness_all_filled():
    data = {
        "required_skills": ["Java"],
        "price_min": 60.0,
        "work_location": "東京",
        "role": "Java案件",
    }
    assert structurer._compute_required_completeness(data, "件名") == 1.0


def test_required_completeness_partial():
    data = {"required_skills": ["Java"]}
    assert structurer._compute_required_completeness(data, "") == 0.25


def test_extract_must_not_patterns():
    body = "外国籍不可\n45歳まで\n出社必須"
    info = structurer._extract_must_not(body)
    assert "外国籍不可" in info["must_not"]
    assert "年齢制限" in info["must_not"]
    assert info["age_max"] == 45
    assert "出社必須" in info["must_not"]


def test_postprocess_sets_quality_flag_when_sparse():
    raw = {"required_skills": [], "remote_ok": "unknown"}
    result = structurer._postprocess_case_json(raw)
    assert result.get("must_not") == []


def test_retry_extraction_merges_on_low_completeness():
    guard = SimpleNamespace(
        can_call=lambda *a, **k: True,
        get_model=lambda: "claude-haiku-4-5-20251001",
        record_cost=lambda *a, **k: None,
    )
    config = SimpleNamespace(anthropic_api_key="secret")
    sparse_json = '{"required_skills":[],"remote_ok":"unknown"}'
    retry_json = '{"required_skills":["Java"],"price_min":70,"price_max":70,"work_location":"東京","role":"Java"}'
    sparse_resp = SimpleNamespace(
        content=[SimpleNamespace(text=sparse_json)],
        usage=SimpleNamespace(input_tokens=10, output_tokens=20),
    )
    retry_resp = SimpleNamespace(
        content=[SimpleNamespace(text=retry_json)],
        usage=SimpleNamespace(input_tokens=10, output_tokens=20),
    )
    body = "内容のみで構造化が必要な案件メール"
    with patch("structurer._rule_based_extract", return_value=structurer._empty_result()):
        with patch("structurer._call_anthropic", return_value=sparse_resp):
            with patch("structurer._call_anthropic_retry", return_value=retry_resp):
                with patch("structurer._ledger_can_spend", return_value=True):
                    result = structurer.structure(body, guard, config)

    assert result.get("extraction_retried") is True
    assert result["field_completeness"] >= 0.6


def test_judge_must_not_foreign_ng():
    case = {
        "required_skills": ["Java"],
        "price_max": 80,
        "extraction_confidence": 1.0,
        "must_not": ["外国籍不可"],
    }
    engineer = {
        "単価（万円）": 60,
        "スキル": ["Java"],
        "国籍": "中国",
        "_last_edited_time": "2026-06-23T00:00:00+00:00",
    }
    result = judge_with_meta(case, engineer, SkillNormalizer("skill_aliases.json"))
    assert result["verdict"] == "NG"
    assert any("外国籍不可" in r for r in result["reasons"])


def test_judge_must_not_age_ng():
    case = {
        "required_skills": ["Java"],
        "price_max": 80,
        "extraction_confidence": 1.0,
        "must_not": ["年齢制限"],
        "age_max": 40,
    }
    engineer = {
        "単価（万円）": 60,
        "スキル": ["Java"],
        "年齢": 45,
        "_last_edited_time": "2026-06-23T00:00:00+00:00",
    }
    result = judge_with_meta(case, engineer, SkillNormalizer("skill_aliases.json"))
    assert result["verdict"] == "NG"
    assert any("年齢制限" in r for r in result["reasons"])


def test_processed_db_extraction_retry_count(tmp_path):
    db = ProcessedDB(tmp_path / "processed.db")
    db.record_extraction_retry(2)
    stats = db.get_today_stats()
    assert stats.get("extraction_retry_count", 0) >= 2
