"""8.25 claim_id=None で success/permanent/transient 各々 idempotent（SPEC v2.10.1）。"""

from __future__ import annotations

import cost_guard as cg
from common.ledger import reserve


def _decision_without_claim(monkeypatch, target_id="proj-no-claim-idem"):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    reservation_id = reserve("research")
    assert reservation_id
    return cg.Decision(
        allowed=True,
        reason=cg.Reasons.ok,
        exit_code=0,
        model="gpt-4o-mini",
        model_class="light",
        estimated_cost=0.001,
        reservation_id=reservation_id,
        dedup_key="",
        claim_id=None,
        script="no_claim_idem",
        phase="research",
        block_type="manual_query",
    )


def test_claim_none_success_idempotent(monkeypatch):
    d = _decision_without_claim(monkeypatch, "proj-no-claim-success")
    r1 = cg.finalize(d, in_tokens=10, out_tokens=10, success=True)
    assert r1.status == cg.FinalizeStatus.OK_RECORDED
    r2 = cg.finalize(d, in_tokens=10, out_tokens=10, success=True)
    assert r2.status == cg.FinalizeStatus.IDEMPOTENT


def test_claim_none_transient_idempotent(monkeypatch):
    d = _decision_without_claim(monkeypatch, "proj-no-claim-transient")
    r1 = cg.finalize(d, success=False, error_kind="transient")
    assert r1.status == cg.FinalizeStatus.OK_RELEASED
    r2 = cg.finalize(d, success=False, error_kind="transient")
    assert r2.status == cg.FinalizeStatus.IDEMPOTENT


def test_claim_none_permanent_idempotent(monkeypatch):
    d = _decision_without_claim(monkeypatch, "proj-no-claim-permanent")
    r1 = cg.finalize(d, success=False, error_kind="permanent_api")
    assert r1.status == cg.FinalizeStatus.OK_RECORDED
    r2 = cg.finalize(d, success=False, error_kind="permanent_api")
    assert r2.status == cg.FinalizeStatus.IDEMPOTENT
