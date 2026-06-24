from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from matcher import is_engineer_fresh, partition_fresh_engineers
from processed_db import ProcessedDB
from staleness_checker import STALENESS_DAYS


def _engineer(days_old: int) -> dict:
    edited = (datetime.now(timezone.utc) - timedelta(days=days_old)).isoformat()
    return {
        "id": f"eng-{days_old}",
        "名前": f"Tester {days_old}",
        "_last_edited_time": edited,
        "単価（万円）": 70,
        "スキル": ["Java"],
        "提案対象フラグ": True,
    }


def test_partition_fresh_engineers_passes_20_day_old():
    fresh, excluded = partition_fresh_engineers([_engineer(20)])

    assert len(fresh) == 1
    assert excluded == 0
    assert is_engineer_fresh(fresh[0]) is True


def test_partition_fresh_engineers_excludes_22_day_old():
    fresh, excluded = partition_fresh_engineers([_engineer(22)])

    assert fresh == []
    assert excluded == 1
    assert is_engineer_fresh(_engineer(22)) is False


def test_staleness_days_loaded_from_matching_rules():
    rules_path = (
        __import__("pathlib").Path(__file__).resolve().parents[2] / "config" / "matching_rules.json"
    )
    data = json.loads(rules_path.read_text(encoding="utf-8"))

    assert data["max_profile_age_days"] == STALENESS_DAYS == 21


def test_record_staleness_excluded_updates_daily_stats(tmp_path):
    db = ProcessedDB(tmp_path / "processed.db")

    db.record_staleness_excluded(3)

    with sqlite3.connect(tmp_path / "processed.db") as conn:
        count = conn.execute(
            "SELECT staleness_excluded_count FROM daily_stats WHERE stat_date = date('now', '+9 hours')"
        ).fetchone()[0]
    assert count == 3


@patch("matching_v3.CostGuard.can_call", return_value=True)
@patch("matching_v3.structurer.structure_case")
def test_process_cases_skips_stale_engineer(structure_case_mock, _can_call_mock, tmp_path):
    import matching_v3

    structure_case_mock.return_value = {
        "required_skills": ["Java"],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    db = ProcessedDB(tmp_path / "processed.db")
    normalizer = matching_v3.SkillNormalizer(matching_v3.BASE_DIR / "skill_aliases.json")
    fresh = _engineer(20)
    stale = _engineer(22)
    cases = [{"id": "case-1", "案件名": "Java", "案件詳細": "Java案件", "_created": "2026-06-23"}]

    matching_v3._process_cases(
        cases,
        [fresh, stale],
        db,
        matching_v3.CostGuard(),
        normalizer,
        matching_v3.Notifier(matching_v3.Config()),
        notion=None,
        dry_run=True,
    )

    with sqlite3.connect(tmp_path / "processed.db") as conn:
        row = conn.execute(
            "SELECT match_results_json FROM processed_cases WHERE case_id = 'case-1'"
        ).fetchone()
        stale_count = conn.execute(
            "SELECT staleness_excluded_count FROM daily_stats WHERE stat_date = date('now', '+9 hours')"
        ).fetchone()[0]

    results = json.loads(row[0])
    engineer_ids = {item["engineer_id"] for item in results}
    assert fresh["id"] in engineer_ids
    assert stale["id"] not in engineer_ids
    assert stale_count == 1
