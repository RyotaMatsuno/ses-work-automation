"""8.26 permanent finalize 再実行が IDEMPOTENT を返す（SPEC v2.10.1）。"""

from __future__ import annotations

import cost_guard as cg


def _make_decision(monkeypatch, target_id="proj-perm-idem-001"):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    d = cg.allowed(
        phase="research",
        block_type="skill_judge",
        target_id=target_id,
        script="perm_idem",
    )
    assert d.allowed
    return d


def test_finalize_permanent_idempotent(monkeypatch):
    d = _make_decision(monkeypatch)
    r1 = cg.finalize(d, in_tokens=50, out_tokens=25, success=False, error_kind="permanent_auth")
    assert r1.status == cg.FinalizeStatus.OK_RECORDED
    r2 = cg.finalize(d, in_tokens=50, out_tokens=25, success=False, error_kind="permanent_auth")
    assert r2.status == cg.FinalizeStatus.IDEMPOTENT
