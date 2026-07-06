from __future__ import annotations

from datetime import date

import pytest

from hard_filters import (
    CaseView,
    EngineerView,
    apply_hard_filters,
    build_case_view,
    build_engineer_view,
    location_compatible,
    rate_compatible,
    skill_compatible,
    start_timing_compatible,
)
from matcher import SkillNormalizer

BASE = __import__("pathlib").Path(__file__).resolve().parents[1]


@pytest.fixture
def normalizer() -> SkillNormalizer:
    return SkillNormalizer(BASE / "skill_aliases.json")


def test_rate_compatible_passes_when_unknown():
    case = CaseView(rate_max_man=None)
    engineer = EngineerView(desired_rate_min=80)
    assert rate_compatible(case, engineer) is True


def test_rate_compatible_rejects_high_engineer_rate():
    case = CaseView(rate_max_man=60, rate_type="fixed_upper_only")
    engineer = EngineerView(desired_rate_min=70)
    assert rate_compatible(case, engineer) is False


def test_rate_compatible_skill_dependent_passes():
    case = CaseView(rate_max_man=60, rate_type="skill_dependent_no_number")
    engineer = EngineerView(desired_rate_min=90)
    assert rate_compatible(case, engineer) is True


def test_location_full_remote_passes():
    case = CaseView(remote_type="full_remote", location_area="東京")
    engineer = EngineerView(commutable_areas={"大阪"})
    assert location_compatible(case, engineer) is True


def test_location_onsite_requires_area():
    case = CaseView(remote_type="onsite", location_area="東京")
    engineer = EngineerView(commutable_areas={"東京"})
    assert location_compatible(case, engineer) is True
    engineer2 = EngineerView(commutable_areas={"大阪"})
    assert location_compatible(case, engineer2) is False


def test_skill_compatible_single_required():
    normalizer = SkillNormalizer(BASE / "skill_aliases.json")
    case = CaseView(required_skills=["Java"])
    engineer = EngineerView(skills=["Java", "Spring"])
    assert skill_compatible(case, engineer, normalizer) is True
    engineer2 = EngineerView(skills=["Python"])
    assert skill_compatible(case, engineer2, normalizer) is False


def test_skill_compatible_half_overlap():
    normalizer = SkillNormalizer(BASE / "skill_aliases.json")
    case = CaseView(required_skills=["Java", "Spring", "AWS"])
    engineer = EngineerView(skills=["Java", "Spring"])
    assert skill_compatible(case, engineer, normalizer) is True
    engineer2 = EngineerView(skills=["Java"])
    assert skill_compatible(case, engineer2, normalizer) is False


def test_start_timing_compatible():
    case = CaseView(start_date=date(2026, 7, 1))
    engineer = EngineerView(available_date=date(2026, 6, 15))
    assert start_timing_compatible(case, engineer) is True
    engineer2 = EngineerView(available_date=date(2026, 8, 1))
    assert start_timing_compatible(case, engineer2) is False


def test_apply_hard_filters_toggle(normalizer: SkillNormalizer):
    case = {"単価（万円）": 60, "rate_type": "fixed_upper_only", "remote_type": "onsite", "勤務地": "東京"}
    case_json = {
        "price_max": 60,
        "required_skills": ["Java"],
        "start_date": "2026-07-01",
        "work_location": "東京",
    }
    engineers = [
        {
            "id": "e1",
            "単価（万円）": 55,
            "居住地": "東京",
            "正規化スキル": ["Java"],
            "稼働可能日": "2026-06-01",
        },
        {
            "id": "e2",
            "単価（万円）": 90,
            "居住地": "東京",
            "正規化スキル": ["Java"],
            "稼働可能日": "2026-06-01",
        },
    ]
    survivors, stats = apply_hard_filters(
        case,
        case_json,
        engineers,
        normalizer,
        filters={"rate": True, "remote_location": True, "skill_threshold": True, "start_timing": True},
    )
    assert len(survivors) == 1
    assert survivors[0]["id"] == "e1"
    assert stats.dropped_rate == 1

    survivors_off, _ = apply_hard_filters(
        case, case_json, engineers, normalizer, filters={"rate": False, "remote_location": False, "skill_threshold": False, "start_timing": False}
    )
    assert len(survivors_off) == 2


def test_build_views_from_notion_fields(normalizer: SkillNormalizer):
    case = {"単価（万円）": 70, "rate_type": "fixed_upper_only", "remote_type": "hybrid", "勤務地": "東京都港区"}
    case_json = {"required_skills": ["Java"], "start_date": "2026-08-01"}
    cv = build_case_view(case, case_json)
    assert cv.rate_max_man == 70
    assert cv.location_area == "東京"

    eng = build_engineer_view({"単価（万円）": 65, "居住地": "東京", "正規化スキル": ["Java"], "稼働可能日": "2026-07-01"})
    assert eng.desired_rate_min == 65
    assert "東京" in eng.commutable_areas
