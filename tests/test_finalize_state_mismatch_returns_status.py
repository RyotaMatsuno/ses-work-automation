"""8.27 reservation/claim 不在・片肺で STATE_MISMATCH 返却（SPEC v2.10.1）。"""

from __future__ import annotations

import cost_guard as cg


def _make_decision(monkeypatch, target_id="proj-mismatch-001"):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    d = cg.allowed(
        phase="research",
        block_type="skill_judge",
        target_id=target_id,
        script="mismatch_test",
    )
    assert d.allowed
    return d


def test_reservation_missing_returns_state_mismatch(monkeypatch):
    d = _make_decision(monkeypatch, "proj-mismatch-res-missing")
    d.reservation_id = "00000000-0000-0000-0000-000000000000"
    result = cg.finalize(d, success=True)
    assert result.status == cg.FinalizeStatus.STATE_MISMATCH
    assert result.detail == "reservation_missing"


def test_claim_missing_returns_state_mismatch(monkeypatch):
    d = _make_decision(monkeypatch, "proj-mismatch-claim-missing")
    d.claim_id = "00000000-0000-0000-0000-000000000000"
    result = cg.finalize(d, success=True)
    assert result.status == cg.FinalizeStatus.STATE_MISMATCH
    assert result.detail == "claim_missing"
