# -*- coding: utf-8 -*-
"""Task W: CostGuard integrity tests (P0-1 / P0-2)."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cost_guard as cg
from common.ledger import cleanup_stale_reservations, reserve
from common.state_store import init_schema, open_conn


def test_db_error_blocked_when_can_spend_raises(monkeypatch):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    monkeypatch.setattr("common.ledger.can_spend", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db locked")))

    decision = cg.allowed(
        phase="research",
        block_type="skill_judge",
        target_id="proj-db-error-001",
        script="db_error_test",
    )

    assert decision.allowed is False
    assert decision.reason == cg.Reasons.db_error_blocked
    assert decision.exit_code == 2

    init_schema()
    conn = open_conn()
    try:
        row = conn.execute(
            "SELECT reason, detail, script FROM event_log WHERE reason=? ORDER BY id DESC LIMIT 1",
            ("db_error_blocked",),
        ).fetchone()
        assert row is not None
        assert row["script"] == "db_error_test"
        assert "db locked" in row["detail"]
    finally:
        conn.close()


def test_cleanup_stale_reservations_releases_orphan(monkeypatch):
    init_schema()
    monkeypatch.setattr("common.ledger.cleanup_stale_reservations", lambda ttl_sec=None: 0)

    reservation_id = reserve("classify")
    assert reservation_id is not None

    conn = open_conn()
    try:
        stale_time = (datetime.now(timezone.utc) - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE reservations SET created_at=? WHERE reservation_id=?",
            (stale_time, reservation_id),
        )
        conn.commit()

        row = conn.execute(
            "SELECT reserved FROM phase_calls WHERE phase=? ORDER BY date DESC LIMIT 1",
            ("classify",),
        ).fetchone()
        assert row is not None
        reserved_before = row["reserved"]

        released = cleanup_stale_reservations(ttl_sec=600)
        assert released == 1

        row = conn.execute(
            "SELECT finalized FROM reservations WHERE reservation_id=?",
            (reservation_id,),
        ).fetchone()
        assert row["finalized"] == 1

        row = conn.execute(
            "SELECT reserved FROM phase_calls WHERE phase=? ORDER BY date DESC LIMIT 1",
            ("classify",),
        ).fetchone()
        assert row["reserved"] == reserved_before - 1
    finally:
        conn.close()


@patch("mail_pipeline.mail_pipeline.classify_email", return_value={"type": "other"})
@patch("mail_pipeline.mail_pipeline.finalize")
@patch("mail_pipeline.mail_pipeline.requests.post")
@patch("mail_pipeline.mail_pipeline._batch_budget_reserve")
@patch("analyze_final.classify_by_rule", return_value="unknown")
def test_classify_email_v2_batch_failure_finalizes_reservation(
    mock_rule, mock_reserve, mock_post, mock_finalize, mock_classify_email
):
    from mail_pipeline import mail_pipeline as mp

    decision = SimpleNamespace(allowed=True, exit_code=0, reservation_id="res-batch-fail", claim_id=None)
    mock_reserve.return_value = decision
    mock_post.return_value = MagicMock(status_code=500, text="server error")

    with patch.object(mp, "ANTHROPIC_KEY", "test-key"):
        result = mp.classify_email_v2(
            [{"index": 0, "subject": "テスト案件", "sender": "a@b.com", "body": "本文"}]
        )

    assert result[0]["type"] == "other"
    mock_finalize.assert_called_once_with(decision, success=False, error_kind="transient")
