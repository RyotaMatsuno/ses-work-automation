"""8.24 transient finalize 再実行が IDEMPOTENT を返す（SPEC v2.10.1）。"""

from __future__ import annotations

import cost_guard as cg


def _make_decision(monkeypatch, target_id="proj-trans-idem-001"):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    d = cg.allowed(
        phase="research",
        block_type="skill_judge",
        target_id=target_id,
        script="transient_idem",
    )
    assert d.allowed
    return d


def test_finalize_transient_idempotent(monkeypatch):
    d = _make_decision(monkeypatch)
    r1 = cg.finalize(d, success=False, error_kind="transient")
    assert r1.status == cg.FinalizeStatus.OK_RELEASED
    r2 = cg.finalize(d, success=False, error_kind="transient")
    assert r2.status == cg.FinalizeStatus.IDEMPOTENT
