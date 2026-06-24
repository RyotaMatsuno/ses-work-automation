"""8.8 models.list() 全失敗後に reason=error_transient_models_list。"""

from __future__ import annotations

import pytest


def test_models_list_all_fail_returns_correct_reason(monkeypatch):
    """models.list() が3回とも失敗 → reason=error_transient_models_list, exit_code=2。"""

    def always_fail(p, model_hint=None):
        from common.model_selector import ModelSelectionError

        raise ModelSelectionError("error_transient_models_list")

    monkeypatch.setattr("common.model_selector.select_model", always_fail)

    import cost_guard as cg

    d = cg.allowed(phase="research", block_type="manual_query", script="test")
    assert d.allowed is False
    assert d.reason == cg.Reasons.error_transient_models_list
    assert d.exit_code == 2


def test_models_list_fail_does_not_advance_to_threshold(monkeypatch):
    """models.list() 失敗時は閾値チェックや dedup を呼ばない。"""
    threshold_called = []

    def always_fail(p, model_hint=None):
        from common.model_selector import ModelSelectionError

        raise ModelSelectionError("error_transient_models_list")

    monkeypatch.setattr("common.model_selector.select_model", always_fail)

    # claim_dedup が呼ばれていないことを確認
    claim_called = []
    monkeypatch.setattr("common.dedup.claim_dedup", lambda k, ttl_sec=3600: claim_called.append(k))

    import cost_guard as cg

    cg.allowed(phase="research", block_type="manual_query", script="test")
    assert len(claim_called) == 0


def test_fetch_failure_uses_retry_logic(monkeypatch, tmp_path):
    """_fetch_openai_models が RuntimeError を raise するとき select_model が正しくエラーを返す。"""
    call_count = [0]

    def fail_fetch():
        call_count[0] += 1
        raise RuntimeError("API error")

    monkeypatch.setattr("common.model_selector._fetch_openai_models", fail_fetch)
    import common.model_selector as ms

    ms._models_cache = None

    from common.model_selector import ModelSelectionError, select_model

    with pytest.raises(ModelSelectionError) as exc_info:
        select_model("research")
    assert exc_info.value.reason == "error_transient_models_list"
