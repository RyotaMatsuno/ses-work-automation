from __future__ import annotations

import sqlite3

import pytest
from processed_db import ProcessedDB


def test_mark_api_called_registers_new_case(tmp_path):
    db = ProcessedDB(tmp_path / "processed.db")

    db.mark_api_called("case-1", "subject", "2026-06-03")

    assert db.is_processed("case-1") is True


def test_update_status_updates_business_status(tmp_path):
    db = ProcessedDB(tmp_path / "processed.db")
    db.mark_api_called("case-1", "subject", "2026-06-03")

    db.update_status("case-1", "structured")

    with sqlite3.connect(tmp_path / "processed.db") as conn:
        status = conn.execute(
            "SELECT business_status FROM processed_cases WHERE case_id = ?",
            ("case-1",),
        ).fetchone()[0]
    assert status == "structured"


def test_update_status_matched_recomputes_daily_stats(tmp_path):
    db = ProcessedDB(tmp_path / "processed.db")
    db.mark_api_called("case-1", "subject", "2026-06-03")

    db.update_status(
        "case-1",
        "matched",
        [{"verdict": "REVIEW", "engineer_id": "eng-1"}],
    )
    db.recompute_daily_stats()

    stats = db.get_today_stats()
    assert stats["review_count"] == 1
    assert stats["match_count"] == 1
    assert stats["ng_count"] == 0


def test_recompute_daily_stats_is_idempotent(tmp_path):
    db = ProcessedDB(tmp_path / "processed.db")
    db.mark_api_called("case-1", "subject", "2026-06-03")
    db.update_status(
        "case-1",
        "matched",
        [{"verdict": "MATCH", "engineer_id": "eng-1"}],
    )
    db.mark_api_called("case-2", "subject2", "2026-06-03")
    db.update_status(
        "case-2",
        "matched",
        [{"verdict": "REVIEW", "engineer_id": "eng-2"}],
    )

    first = db.recompute_daily_stats()
    second = db.recompute_daily_stats()

    assert first == second
    assert first["match_count"] == 2
    assert first["review_count"] == 1


def test_backfill_daily_stats_updates_past_dates(tmp_path, monkeypatch):
    db = ProcessedDB(tmp_path / "processed.db")
    with sqlite3.connect(tmp_path / "processed.db") as conn:
        conn.execute(
            """
            INSERT INTO processed_cases (
                case_id, business_status, match_results_json, api_called, updated_at
            )
            VALUES (?, 'matched', ?, 1, ?)
            """,
            (
                "past-case",
                '[{"verdict": "REVIEW", "engineer_id": "eng-1"}]',
                "2026-06-23 10:00:00",
            ),
        )

    results = db.backfill_daily_stats()

    assert len(results) == 1
    assert results[0]["stat_date"] == "2026-06-23"
    assert results[0]["match_count"] == 1
    assert results[0]["review_count"] == 1


def test_error_case_is_retryable_until_three_attempts(tmp_path):
    db = ProcessedDB(tmp_path / "processed.db")
    db.mark_api_called("case-1", "subject", "2026-06-03")
    db.update_status("case-1", "ERROR")

    assert db.is_processed("case-1") is False

    db.increment_retry("case-1")
    db.increment_retry("case-1")
    db.increment_retry("case-1")

    assert db.is_processed("case-1") is True


def test_add_cost_accumulates(tmp_path):
    db = ProcessedDB(tmp_path / "processed.db")

    db.add_cost("case-1", 0.1)
    db.add_cost("case-1", 0.2)

    with sqlite3.connect(tmp_path / "processed.db") as conn:
        cost = conn.execute(
            "SELECT total_cost_usd FROM processed_cases WHERE case_id = ?",
            ("case-1",),
        ).fetchone()[0]
    assert cost == pytest.approx(0.3)
