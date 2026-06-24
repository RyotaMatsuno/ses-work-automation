"""8.32 finalize() の返り値型 FinalizeResult 検証（SPEC v2.10.1）。"""

from __future__ import annotations

import cost_guard as cg


def test_finalize_returns_finalize_result(monkeypatch):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    d = cg.allowed(
        phase="research",
        block_type="manual_query",
        target_id="",
        script="result_type_test",
    )
    assert d.allowed
    result = cg.finalize(d, in_tokens=10, out_tokens=10, success=True)
    assert isinstance(result, cg.FinalizeResult)
    assert result.status == cg.FinalizeStatus.OK_RECORDED
    assert result.detail == ""
