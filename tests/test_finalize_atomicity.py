"""8.23 finalize 内の中途失敗で全操作が ROLLBACK され、event_log に記録される（SPEC §3.2.2 / v2.10.1）。"""

from __future__ import annotations

from datetime import datetime, timezone

import cost_guard as cg
from common.state_store import init_schema, open_conn


def _make_allowed(monkeypatch, target_id="proj-atom-001"):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    d = cg.allowed(phase="research", block_type="skill_judge", target_id=target_id, script="atomicity_test")
    assert d.allowed is True
    return d


def test_finalize_rollback_on_confirm_dedup_failure(monkeypatch):
    """_record_in_tx 成功後に _confirm_dedup_in_tx が StateMismatchError になると ROLLBACK される。"""
    d = _make_allowed(monkeypatch)

    init_schema()
    conn = open_conn()
    try:
        row = conn.execute(
            "SELECT monthly_usd FROM monthly_state WHERE month=?", (datetime.now(timezone.utc).strftime("%Y-%m"),)
        ).fetchone()
        monthly_before = row["monthly_usd"] if row else 0.0
    finally:
        conn.close()

    from common.ledger import StateMismatchError

    def failing_confirm(conn, claim_id, error=False):
        raise StateMismatchError("Injected failure in confirm_dedup")

    monkeypatch.setattr("common.ledger._confirm_dedup_in_tx", failing_confirm)

    result = cg.finalize(d, in_tokens=100, out_tokens=50, success=True)
    assert result.status == cg.FinalizeStatus.STATE_MISMATCH

    conn = open_conn()
    try:
        row = conn.execute(
            "SELECT monthly_usd FROM monthly_state WHERE month=?", (datetime.now(timezone.utc).strftime("%Y-%m"),)
        ).fetchone()
        monthly_after = row["monthly_usd"] if row else 0.0
    finally:
        conn.close()

    assert abs(monthly_after - monthly_before) < 0.0001


def test_finalize_mismatch_logged_to_event_log(monkeypatch):
    """mismatch ログが rollback 後の別 tx で永続化される。"""
    d = _make_allowed(monkeypatch, target_id="proj-atom-mismatch")

    from common.ledger import StateMismatchError

    def failing_confirm(conn, claim_id, error=False):
        raise StateMismatchError("Injected for event_log test")

    monkeypatch.setattr("common.ledger._confirm_dedup_in_tx", failing_confirm)

    result = cg.finalize(d, in_tokens=10, out_tokens=10, success=True)
    assert result.status == cg.FinalizeStatus.STATE_MISMATCH

    conn = open_conn()
    try:
        row = conn.execute(
            "SELECT detail, script FROM event_log WHERE reason=? ORDER BY id DESC LIMIT 1", ("error_internal",)
        ).fetchone()
        assert row is not None
        assert row["detail"].startswith("finalize_state_mismatch:")
        assert row["script"] == "atomicity_test"
    finally:
        conn.close()
