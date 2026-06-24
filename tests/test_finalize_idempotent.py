"""8.13d finalize を2回呼んでも安全（冪等性）（SPEC §7.2 / v2.10.1）。"""

from __future__ import annotations

import cost_guard as cg


def _make_decision(monkeypatch):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    d = cg.allowed(phase="research", block_type="manual_query", target_id="", script="test")
    assert d.allowed is True
    return d


def test_finalize_twice_success(monkeypatch):
    """成功で finalize → 2回目は IDEMPOTENT。"""
    d = _make_decision(monkeypatch)
    r1 = cg.finalize(d, in_tokens=100, out_tokens=50, success=True)
    assert r1.status == cg.FinalizeStatus.OK_RECORDED
    r2 = cg.finalize(d, in_tokens=100, out_tokens=50, success=True)
    assert r2.status == cg.FinalizeStatus.IDEMPOTENT


def test_finalize_twice_transient(monkeypatch):
    """transient で finalize → 2回目は IDEMPOTENT。"""
    d = _make_decision(monkeypatch)
    r1 = cg.finalize(d, success=False, error_kind="transient")
    assert r1.status == cg.FinalizeStatus.OK_RELEASED
    r2 = cg.finalize(d, success=False, error_kind="transient")
    assert r2.status == cg.FinalizeStatus.IDEMPOTENT


def test_finalize_not_allowed_noop(monkeypatch):
    """allowed=False の Decision で finalize を呼ぶと IDEMPOTENT。"""
    from common.model_selector import ModelSelectionError

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: (_ for _ in ()).throw(ModelSelectionError("error_transient_models_list")),
    )
    d = cg.allowed(phase="research", block_type="manual_query", script="test")
    assert d.allowed is False
    r = cg.finalize(d, success=True)
    assert r.status == cg.FinalizeStatus.IDEMPOTENT
