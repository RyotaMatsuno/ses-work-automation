"""8.29 allowed() の stopped_budget で lock 起きない（SPEC v2.10.1）。"""

from __future__ import annotations

import cost_guard as cg
from common.state_store import init_schema, open_conn


def test_stopped_budget_logs_detail_in_event_log(monkeypatch):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    monkeypatch.setattr("common.ledger.can_spend", lambda *a, **k: False)

    d = cg.allowed(
        phase="research",
        block_type="skill_judge",
        target_id="proj-budget-lock-001",
        script="budget_lock_test",
    )
    assert d.allowed is False
    assert d.reason == cg.Reasons.stopped_budget
    assert "daily_usd=" in d.detail
    assert "monthly_usd=" in d.detail

    init_schema()
    conn = open_conn()
    try:
        row = conn.execute(
            "SELECT detail, script FROM event_log WHERE reason=? ORDER BY id DESC LIMIT 1",
            ("stopped_budget",),
        ).fetchone()
        assert row is not None
        assert "daily_usd=" in row["detail"]
        assert row["script"] == "budget_lock_test"
    finally:
        conn.close()
