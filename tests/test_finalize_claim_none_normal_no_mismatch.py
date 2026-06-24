"""8.33 claim_id=None の正常 finalize が mismatch にならない（SPEC v2.10.1）。"""

from __future__ import annotations

import cost_guard as cg
from common.ledger import reserve


def test_claim_none_success_no_mismatch(monkeypatch):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    reservation_id = reserve("research")
    assert reservation_id

    d = cg.Decision(
        allowed=True,
        reason=cg.Reasons.ok,
        exit_code=0,
        model="gpt-4o-mini",
        model_class="light",
        estimated_cost=0.001,
        reservation_id=reservation_id,
        dedup_key="",
        claim_id=None,
        script="no_claim_normal",
        phase="research",
        block_type="manual_query",
    )
    result = cg.finalize(d, in_tokens=10, out_tokens=10, success=True)
    assert result.status == cg.FinalizeStatus.OK_RECORDED
