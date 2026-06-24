from __future__ import annotations

import sys
from pathlib import Path

MATCHING_V3 = Path(__file__).resolve().parents[1]
if str(MATCHING_V3) not in sys.path:
    sys.path.insert(0, str(MATCHING_V3))

from matcher import (  # noqa: E402
    SkillNormalizer,
    extract_skills_from_text,
    judge_with_meta,
    prepare_engineer_skills,
    resolve_case_required_skills,
)
from notion_client import NotionClient  # noqa: E402


def _normalizer() -> SkillNormalizer:
    return SkillNormalizer(MATCHING_V3 / "skill_aliases.json")


def test_resolve_required_skills_from_notion_multi_select():
    normalizer = _normalizer()
    case = {"必要スキル": ["java", "AWS"], "案件名": "Python案件"}
    case_json = {"required_skills": []}

    skills, source = resolve_case_required_skills(case, case_json, normalizer)

    assert "Java" in skills
    assert "AWS" in skills
    assert source == "multi_select"


def test_resolve_required_skills_fallback_from_title():
    normalizer = _normalizer()
    case = {
        "必要スキル": [],
        "案件名": "【急募】Java/AWS開発エンジニア募集",
        "案件詳細": "",
        "案件情報原文": "",
    }
    case_json = {"required_skills": []}

    skills, source = resolve_case_required_skills(case, case_json, normalizer)

    assert "Java" in skills
    assert "AWS" in skills
    assert source == "fallback_title"


def test_resolve_required_skills_fallback_from_detail_when_title_empty():
    normalizer = _normalizer()
    case = {
        "必要スキル": [],
        "案件名": "案件A",
        "案件詳細": "必須: PHP, MySQL",
        "案件情報原文": "",
    }
    case_json = {"required_skills": []}

    skills, source = resolve_case_required_skills(case, case_json, normalizer)

    assert "PHP" in skills
    assert "MySQL" in skills
    assert source == "fallback_detail"


def test_judge_runs_with_fallback_skills():
    normalizer = _normalizer()
    case_json = {
        "required_skills": ["Java"],
        "price_max": 72,
        "extraction_confidence": 0.8,
    }
    engineer = {
        "名前": "山田",
        "スキル": ["Java", "Spring"],
        "単価（万円）": 60,
        "備考（LINEメモ）": "",
        "_last_edited_time": "2026-06-01T00:00:00+00:00",
    }
    prepared = prepare_engineer_skills(engineer, normalizer)
    result = judge_with_meta(case_json, prepared, normalizer)

    assert result["verdict"] in ("MATCH", "REVIEW", "PARTIAL_MATCH")
    assert prepared["正規化スキル"] == ["Java", "Spring"]


def test_prepare_engineer_skills_normalizes_multi_select():
    normalizer = _normalizer()
    engineer = {"スキル": ["java", "php"], "単価（万円）": 40}

    prepared = prepare_engineer_skills(engineer, normalizer)

    assert prepared["正規化スキル"] == ["Java", "PHP"]
    assert prepared["単価（万円）"] == 40


def test_parse_case_page_includes_fallback_fields():
    page = {
        "id": "case-1",
        "created_time": "2026-06-01T00:00:00.000Z",
        "last_edited_time": "2026-06-01T00:00:00.000Z",
        "properties": {
            "案件名": {"title": [{"plain_text": "Java案件"}]},
            "案件詳細": {"rich_text": [{"plain_text": "詳細本文"}]},
            "案件情報原文": {"rich_text": [{"plain_text": "原文"}]},
            "必要スキル": {"multi_select": [{"name": "Java"}]},
            "尚可スキル": {"multi_select": [{"name": "AWS"}]},
            "単価（万円）": {"number": 70},
            "仕入単価（万円）": {"number": 60},
            "勤務地": {"rich_text": [{"plain_text": "東京"}]},
            "リモート": {"select": {"name": "可"}},
            "年齢制限": {"rich_text": [{"plain_text": "45歳まで"}]},
        },
    }

    parsed = NotionClient._parse_case_page(page)

    assert parsed["案件情報原文"] == "原文"
    assert parsed["尚可スキル"] == ["AWS"]
    assert parsed["単価（万円）"] == 70
    assert parsed["仕入単価（万円）"] == 60
    assert parsed["勤務地"] == "東京"
    assert parsed["リモート"] == "可"


def test_parse_engineer_page_reads_multi_select_skill_and_price():
    page = {
        "id": "eng-1",
        "last_edited_time": "2026-06-01T00:00:00.000Z",
        "properties": {
            "名前": {"title": [{"plain_text": "YS"}]},
            "スキル": {"multi_select": [{"name": "PHP"}, {"name": "Java"}]},
            "単価（万円）": {"number": 40},
            "稼働状況": {"select": {"name": "稼働可能"}},
            "稼働可能日": {"date": {"start": "2026-07-01"}},
            "居住地": {"select": {"name": "東京"}},
        },
    }

    parsed = NotionClient._parse_engineer_page(page)

    assert parsed["スキル"] == ["PHP", "Java"]
    assert parsed["単価（万円）"] == 40
    assert parsed["稼働可能日"] == "2026-07-01"
    assert parsed["居住地"] == "東京"


def test_extract_skills_from_text_finds_alias():
    normalizer = _normalizer()
    found = extract_skills_from_text("spring boot / java 開発", normalizer)

    assert "Java" in found
