from __future__ import annotations

from pathlib import Path

import pytest

from matcher import (
    SkillNormalizer,
    apply_hard_filter_v6,
    build_skill_index,
    filter_candidates_3layer,
    score_candidate_soft,
)

BASE = Path(__file__).resolve().parents[1]


@pytest.fixture
def normalizer() -> SkillNormalizer:
    return SkillNormalizer(BASE / "skill_aliases.json")


def _engineer(
    eng_id: str,
    *,
    proposal: bool = True,
    status: str = "待機中",
    available: str = "2026-06-01",
    station: str = "新宿",
    years: float = 5,
    skills: list[str] | None = None,
) -> dict:
    return {
        "id": eng_id,
        "名前": eng_id,
        "提案対象フラグ": proposal,
        "稼働状況": status,
        "稼働可能日": available,
        "最寄り駅": station,
        "経験年数": years,
        "正規化スキル": skills or ["Java", "Spring"],
    }


def test_hard_filter_v6_drops_proposal_and_active(normalizer: SkillNormalizer):
    engineers = [
        _engineer("ok"),
        _engineer("no-proposal", proposal=False),
        _engineer("working", status="稼働中"),
    ]
    case_json = {"start_date": "2026-06-01"}
    survivors, breakdowns, stats = apply_hard_filter_v6(engineers, case_json)
    assert [e["id"] for e in survivors] == ["ok"]
    assert stats.dropped_proposal_flag == 1
    assert stats.dropped_active_working == 1
    assert len(breakdowns) == 3


def test_hard_filter_v6_drops_late_start(normalizer: SkillNormalizer):
    engineers = [_engineer("late", available="2026-12-01")]
    case_json = {"start_date": "2026-06-01"}
    survivors, _, stats = apply_hard_filter_v6(engineers, case_json)
    assert survivors == []
    assert stats.dropped_late_start == 1


def test_soft_scoring_prefers_better_skill_match(normalizer: SkillNormalizer):
    engineers = [
        _engineer("weak", skills=["Python"]),
        _engineer("strong", skills=["Java", "Spring"]),
    ]
    skill_index = build_skill_index(engineers, normalizer)
    case_json = {
        "start_date": "2026-06-01",
        "work_location": "新宿",
        "experience_years": 3,
        "required_skills": ["Java", "Spring"],
    }
    weak = score_candidate_soft(engineers[0], case_json, normalizer, skill_index, ["Java", "Spring"])
    strong = score_candidate_soft(engineers[1], case_json, normalizer, skill_index, ["Java", "Spring"])
    assert strong["scores"]["total"] > weak["scores"]["total"]


def test_filter_candidates_3layer_reranks_top_n(normalizer: SkillNormalizer):
    engineers = [
        _engineer("a", skills=["Python"], station="大阪"),
        _engineer("b", skills=["Java", "Spring"], station="新宿"),
        _engineer("c", skills=["Java"], station="渋谷"),
    ]
    skill_index = build_skill_index(engineers, normalizer)
    case = {}
    case_json = {
        "start_date": "2026-06-01",
        "work_location": "新宿",
        "experience_years": 3,
        "required_skills": ["Java", "Spring"],
    }
    candidates, breakdowns, stats = filter_candidates_3layer(
        engineers,
        case,
        case_json,
        normalizer,
        skill_index,
        ["Java", "Spring"],
        max_candidates=2,
    )
    assert len(candidates) == 2
    assert candidates[0]["id"] == "b"
    assert stats.total_in == 3
    assert all("scores" in item or "rejection_reasons" in item for item in breakdowns)
