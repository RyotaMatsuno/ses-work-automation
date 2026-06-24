"""8.19 finalize の不正引数組み合わせで ValueError が raise される（SPEC §7.1）。"""

from __future__ import annotations

import pytest


def _make_allowed(monkeypatch):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    import cost_guard as cg

    d = cg.allowed(phase="research", block_type="manual_query", script="test")
    assert d.allowed is True
    return d


def test_success_false_error_kind_empty_raises_value_error(monkeypatch):
    """success=False かつ error_kind="" → ValueError を raise する。"""
    import cost_guard as cg

    d = _make_allowed(monkeypatch)
    with pytest.raises(ValueError, match="error_kind required when success=False"):
        cg.finalize(d, success=False, error_kind="")


def test_success_true_error_kind_nonempty_raises_value_error(monkeypatch):
    """success=True かつ error_kind!="" → ValueError を raise する。"""
    import cost_guard as cg

    d = _make_allowed(monkeypatch)
    with pytest.raises(ValueError, match="error_kind must be empty when success=True"):
        cg.finalize(d, success=True, error_kind="transient")


def test_valid_success_true_no_error(monkeypatch):
    """success=True, error_kind="" は正常（ValueError なし）。"""
    import cost_guard as cg

    d = _make_allowed(monkeypatch)
    cg.finalize(d, success=True, error_kind="")  # 例外なし


def test_valid_success_false_transient_no_error(monkeypatch):
    """success=False, error_kind="transient" は正常。"""
    import cost_guard as cg

    d = _make_allowed(monkeypatch)
    cg.finalize(d, success=False, error_kind="transient")  # 例外なし
