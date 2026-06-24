"""8.34 log_event 失敗時でも FinalizeResult(STATE_MISMATCH) は返る（SPEC v2.10.1）。"""

from __future__ import annotations

import cost_guard as cg


def test_finalize_log_event_failure_handled(monkeypatch):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    d = cg.allowed(
        phase="research",
        block_type="skill_judge",
        target_id="proj-log-fail-001",
        script="log_fail_test",
    )
    assert d.allowed
    d.reservation_id = "00000000-0000-0000-0000-000000000088"

    def boom(*args, **kwargs):
        raise RuntimeError("log_event unavailable")

    monkeypatch.setattr("common.ledger.log_event", boom)

    result = cg.finalize(d, success=True)
    assert result.status == cg.FinalizeStatus.STATE_MISMATCH
    assert result.detail == "reservation_missing"
