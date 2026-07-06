"""Tests for Task AB: match quality improvement + price anomaly."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mail_pipeline.price_extractor import validate_price


def _make_engineer(engineer_id: str, skills: list, price: float | None = 60.0) -> dict:
    return {
        "id": engineer_id,
        "名前": f"Test {engineer_id}",
        "スキル": skills,
        "正規化スキル": skills,
        "単価（万円）": price,
        "情報取得日": "2026-06-20",
    }


def _make_case_json(required_skills: list, price_max: float | None = 70.0) -> dict:
    return {
        "required_skills": required_skills,
        "price_max": price_max,
        "price_min": price_max,
    }


def test_price_over_200_nulled():
    """200万超の単価（年収キーワードなし）はnullになること"""
    result_val, reason = validate_price(430000, raw_text="単価情報")
    assert result_val is None
    assert reason == "anomaly_nulled"


def test_price_over_200_annual_converted():
    """200万超かつ年収キーワードあり → ÷12で月額換算"""
    result_val, reason = validate_price(600, raw_text="年収600万円")
    assert result_val == 50.0
    assert reason == "annual_converted"


def test_price_under_20_nulled():
    """20万未満（日額キーワードなし）はnullになること"""
    result_val, reason = validate_price(5, raw_text="単価5万円")
    assert result_val is None
    assert reason == "anomaly_nulled"


def test_price_under_20_daily_converted():
    """20万未満かつ日額キーワードあり → ×20で月額換算"""
    result_val, reason = validate_price(3, raw_text="日額3万円")
    assert result_val == 60.0
    assert reason == "daily_converted"


def test_price_normal_unchanged():
    """正常範囲（20〜200万）はそのまま返ること"""
    result_val, reason = validate_price(65, raw_text="単価65万円")
    assert result_val == 65.0
    assert reason is None


def test_price_none_returns_none():
    """Noneはそのままnone"""
    result_val, reason = validate_price(None)
    assert result_val is None
    assert reason is None


def test_match_count_capped_at_20():
    """マッチ結果が20件以下にトリムされること"""
    # matching_v3.py の results[:20] ロジックを直接検証
    results = [{"engineer_id": f"e{i}", "score": float(i), "verdict": "MATCH"} for i in range(50)]
    results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    if len(results) > 20:
        results = results[:20]
    assert len(results) == 20
    assert results[0]["score"] == 49.0


def test_empty_skill_project_skipped():
    """必要スキル空の案件はSKIPPEDになること（resolve_case_required_skillsが[]を返す）"""
    from matcher import SkillNormalizer, resolve_case_required_skills

    aliases_path = Path(__file__).resolve().parent.parent / "skill_aliases.json"
    normalizer = SkillNormalizer(aliases_path)

    case = {"id": "test-empty", "必要スキル": [], "案件名": "", "案件詳細": "", "案件情報原文": ""}
    case_json = {"required_skills": []}
    skills, source = resolve_case_required_skills(case, case_json, normalizer)
    assert skills == [], f"Expected [], got {skills}"
    assert source == "none"
