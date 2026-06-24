from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from unittest.mock import patch

from matcher import SkillNormalizer, build_skill_index, filter_engineers_by_required_skills
from processed_db import ProcessedDB


def _engineer(eid: str, skills: list[str]) -> dict:
    return {
        "id": eid,
        "名前": eid,
        "スキル": skills,
        "単価（万円）": 60,
        "_last_edited_time": datetime.now(timezone.utc).isoformat(),
    }


def test_skill_index_filters_candidates(tmp_path):
    normalizer = SkillNormalizer("skill_aliases.json")
    engineers = [
        _engineer("e1", ["Java", "Spring"]),
        _engineer("e2", ["Python"]),
        _engineer("e3", ["Java"]),
    ]
    index = build_skill_index(engineers, normalizer)
    filtered = filter_engineers_by_required_skills(
        engineers,
        normalizer,
        index,
        ["Java", "Spring"],
    )
    assert len(filtered) == 1
    assert filtered[0]["id"] == "e1"


def test_skill_index_returns_empty_when_no_engineer_matches_all_required():
    normalizer = SkillNormalizer("skill_aliases.json")
    engineers = [
        _engineer("e1", ["Java"]),
        _engineer("e2", ["Spring"]),
    ]
    index = build_skill_index(engineers, normalizer)
    filtered = filter_engineers_by_required_skills(
        engineers,
        normalizer,
        index,
        ["Java", "Spring"],
    )
    assert filtered == []


def test_should_skip_unchanged_matched_case(tmp_path):
    db = ProcessedDB(tmp_path / "processed.db")
    case_id = "case-1"
    edited = "2026-06-23T10:00:00Z"
    db.update_status(case_id, "matched", [], case_last_edited_at=edited)

    assert db.should_skip_unchanged_case(case_id, edited) is True
    assert db.should_skip_unchanged_case(case_id, "2026-06-23T11:00:00Z") is False


def test_should_skip_unchanged_ng_case(tmp_path):
    db = ProcessedDB(tmp_path / "processed.db")
    case_id = "case-ng"
    edited = "2026-06-23T10:00:00Z"
    db.update_status(case_id, "ng", [], case_last_edited_at=edited)

    assert db.should_skip_unchanged_case(case_id, edited) is True
    assert db.should_skip_unchanged_case(case_id, "2026-06-23T12:00:00Z") is False


@patch("matching_v3.CostGuard.can_call", return_value=True)
@patch("matching_v3.structurer.structure_case")
def test_process_cases_marks_ng_when_no_match(structure_case_mock, _can_call_mock, tmp_path):
    import matching_v3

    structure_case_mock.return_value = {
        "required_skills": ["Cobol"],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    db = ProcessedDB(tmp_path / "processed.db")
    normalizer = matching_v3.SkillNormalizer(matching_v3.BASE_DIR / "skill_aliases.json")
    engineer = _engineer("e1", ["Java"])
    cases = [{"id": "case-ng-1", "案件名": "Cobol", "案件詳細": "Cobol案件", "_created": "2026-06-23"}]

    matching_v3._process_cases(
        cases,
        [engineer],
        db,
        matching_v3.CostGuard(),
        normalizer,
        matching_v3.Notifier(matching_v3.Config()),
        notion=None,
        dry_run=True,
    )

    with sqlite3.connect(tmp_path / "processed.db") as conn:
        row = conn.execute(
            "SELECT business_status, match_results_json FROM processed_cases WHERE case_id = 'case-ng-1'"
        ).fetchone()

    assert row[0] == "ng"
    assert json.loads(row[1]) == []
