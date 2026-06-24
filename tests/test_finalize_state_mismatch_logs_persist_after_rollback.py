"""8.28 mismatch ログが rollback 後の別 tx で永続化される（SPEC v2.10.1 致命点）。"""

from __future__ import annotations

import cost_guard as cg
from common.state_store import init_schema, open_conn


def _make_decision(monkeypatch, target_id="proj-log-persist-001"):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    d = cg.allowed(
        phase="research",
        block_type="skill_judge",
        target_id=target_id,
        script="persist_log_test",
    )
    assert d.allowed
    return d


def test_mismatch_log_persists_after_rollback(monkeypatch):
    d = _make_decision(monkeypatch)
    d.reservation_id = "00000000-0000-0000-0000-000000000099"

    result = cg.finalize(d, success=True)
    assert result.status == cg.FinalizeStatus.STATE_MISMATCH

    init_schema()
    conn = open_conn()
    try:
        rows = conn.execute(
            "SELECT detail, script FROM event_log WHERE reason=? ORDER BY id DESC LIMIT 5",
            ("error_internal",),
        ).fetchall()
        assert any(
            r["detail"].startswith("finalize_state_mismatch:") and r["script"] == "persist_log_test" for r in rows
        )
    finally:
        conn.close()
